#! /usr/bin/env python3
# pylint: disable=invalid-name,line-too-long
"""Visit folder tree report mime-type statistics."""
import collections
import copy
import csv
import datetime as dti
import hashlib
import json
import lzma
import os
import pathlib
import subprocess
import sys

from git import Repo
from git.exc import InvalidGitRepositoryError

ENCODING = 'utf-8'
ENCODING_ERRORS_POLICY = 'ignore'

HASH_POLICY = 'sha256'
HASH_POLICIES_KNOWN = (HASH_POLICY,)

PROXY_DB = 'MIME_TYPES_PROXY_DB'

TS_FORMAT_HR = '%Y-%m-%d %H:%M:%S'
TS_FORMAT_DB = '%Y%m%dT%H%M%SZ'
GIGA = 2 << (30 - 1)
BUFFER_BYTES = 2 << 15

STORE_ROOT = '.lumikko-store'
STORE_PATH_ENTER = pathlib.Path(STORE_ROOT, 'enter')
STORE_PATH_TOMBS = pathlib.Path(STORE_ROOT, 'tombs')
STORE_PATH_PROXY = pathlib.Path(STORE_ROOT, 'proxy')

XZ_FILTERS = [{'id': lzma.FILTER_LZMA2, 'preset': 7 | lzma.PRESET_EXTREME}]
XZ_EXT = '.xz'


def archive(stream, file_path):
    """Create .xz files for long term storage."""
    file_path = pathlib.Path(file_path)  # HACK A DID ACK
    if file_path.suffixes[-1] != XZ_EXT:
        file_path = file_path.with_suffix(file_path.suffix + XZ_EXT)
    with lzma.open(file_path, 'w', check=lzma.CHECK_SHA256, filters=XZ_FILTERS) as f:
        for entry in stream:
            f.write(entry.encode(encoding=ENCODING, errors=ENCODING_ERRORS_POLICY))


def load(proxy_db_path):
    """Load the proxy data as dict."""
    file_path = pathlib.Path(proxy_db_path)  # HACK A DID ACK
    if file_path.is_dir():
        file_path = pathlib.Path(sorted(file_path.glob('*'))[-1])
        print(f'Found latest proxy source as {file_path}')
    else:
        print(f'Recieved latest proxy source as {file_path}')

    if not file_path.is_file():
        raise FileNotFoundError('bootstap f proxy file reading failed.')
    if file_path.suffixes[-1] == XZ_EXT:
        with lzma.open(file_path, mode='rt', encoding=ENCODING, errors=ENCODING_ERRORS_POLICY) as handle:
            return {row[0]: row[0:] for row in csv.reader(handle, delimiter=',', quotechar='|')}
    else:
        with open(file_path, newline='') as handle:
            return {row[0]: row[0:] for row in csv.reader(handle, delimiter=',', quotechar='|')}


def by_name(text, hash_length):
    """Fast and shallow hash rep validity probe."""
    hash_rep_length, base = hash_length, 16
    if len(text) != hash_rep_length:
        return False
    try:
        _ = int(text, base)
    except ValueError:
        return False
    return True


def possible_hash(text, hash_policy=HASH_POLICY):
    """Fast and shallow hash rep validity probe."""
    probe = {
        HASH_POLICY: 64,
        'sha1': 40,
    }
    return by_name(text, probe[hash_policy])


def naive_timestamp(timestamp=None):
    """Logging helper."""
    if timestamp:
        return timestamp.strftime(TS_FORMAT_HR)
    return dti.datetime.now().strftime(TS_FORMAT_HR)


def db_timestamp(timestamp=None):
    """Logging helper."""
    if timestamp:
        return timestamp.strftime(TS_FORMAT_DB)
    return dti.datetime.now().strftime(TS_FORMAT_DB)


def spider_tree(base_path):
    """Visit all elements in the folders below base path and yeld count."""
    return sum(1 for _ in pathlib.Path(base_path).rglob('**/*'))


def walk_files(base_path):
    """Visit the files in the folders below base path in sorted order."""
    for file_path in sorted(base_path.rglob('**/*')):
        yield file_path


def elf_hash(some_bytes: bytes):
    """The ELF hash (Extremely Lossy Function - also used in ELF format).
    unsigned long ElfHash(const unsigned char *s) {
        unsigned long h = 0, high;
        while (*s) {
            h = (h << 4) + *s++;
            if (high = h & 0xF0000000)
                h ^= high >> 24;
            h &= ~high;
        }
        return h;
    }
    """
    h = 0
    for s in some_bytes:
        h = (h << 4) + s
        high = h & 0xF0000000
        if high:
            h ^= high >> 24
        h &= ~high
    return h


def hash_file(path_string):
    """Yield hashes of implicit algorithm of path."""
    path = pathlib.Path(path_string)
    if not path.is_file():
        raise IOError('path is no file for hashing.')

    value = hashlib.sha256()
    with open(path, 'rb') as in_file:
        for byte_block in iter(lambda in_f=in_file: in_f.read(BUFFER_BYTES), b''):
            value.update(byte_block)

    return value.hexdigest()


def count_lines(path_string):
    """Yield number of newline chars (\\n) of path."""
    path = pathlib.Path(path_string)
    if not path.is_file():
        raise IOError('path is no file for line count.')

    value = 0
    with open(path, 'rb') as in_file:
        for byte_block in iter(lambda in_f=in_file: in_f.read(BUFFER_BYTES), b''):
            value += byte_block.count(b'\n')

    return value


def hashes(path_string, algorithms=None):
    """Yield hashes per algorithms of path."""
    if algorithms is None:
        algorithms = {HASH_POLICY: hashlib.sha256}
    for key in algorithms:
        if key not in HASH_POLICIES_KNOWN:
            raise ValueError('hashes received unexpected algorithm key.')

    path = pathlib.Path(path_string)
    if not path.is_file():
        raise IOError('path is no file.')

    accumulator = {k: f() for k, f in algorithms.items()}
    with open(path, 'rb') as in_file:
        for byte_block in iter(lambda in_f=in_file: in_f.read(BUFFER_BYTES), b''):
            for k in algorithms:
                accumulator[k].update(byte_block)

    return {k: f.hexdigest() for k, f in accumulator.items()}


def file_metrics(file_path):
    """Retrieve the file stats."""
    return file_path.stat()


def mime_type(file_path):
    """Either yield mime type from find command without file name in result or arti/choke"""
    find_type = ['file', '--mime', file_path]
    try:
        output = subprocess.check_output(find_type, stderr=subprocess.STDOUT).decode()
        if not output.strip().endswith('(No such file or directory)'):
            return output.strip().split(':', 1)[1].strip()
    except subprocess.CalledProcessError:
        pass  # for now
    return 'arti/choke'


def serialize(storage_hash, line_count, f_stat, fps, file_type):
    """x"""  # TODO(sthagen) round trip has become a mess - fix it
    size_bytes, c_time, m_time = f_stat.st_size, f_stat.st_ctime, f_stat.st_mtime
    return f"{','.join((storage_hash, str(line_count), str(size_bytes), str(c_time), str(m_time), fps, file_type))}\n"


def gen_out_stream(kind):
    """DRY"""
    for v in kind.values():
        yield f"{','.join(v)}\n"


def derive_fingerprints(algorithms, file_path):
    fingerprints = hashes(file_path, algorithms)
    fps = f'{",".join([f"{k}:{v}" for k, v in fingerprints.items()])}'
    return fps


def visit_store(at, hash_policy, algorithms, enter, proxy, update):
    """Here we walk the tree and dispatch."""
    mime_types = collections.Counter()
    mime_sizes, mime_lines = {}, {}
    found_bytes, public, private, non_file = 0, 0, 0, 0
    for file_path in walk_files(pathlib.Path(at)):
        if file_path.name.startswith('.') or '/.' in str(file_path):
            private += 1
            continue
        public += 1
        storage_name = str(file_path)
        if not file_path.is_file():
            non_file += 1
            continue
        storage_hash = hash_file(file_path)
        f_stat = file_metrics(file_path)
        mt = mime_type(file_path)
        mime, charset = '', ''
        if ';' in mt:
            mime, charset = mt.split(';', 1)
        line_count = None
        if mime.startswith('text/') or mime.endswith('xml') or mime.endswith('script'):
            line_count = count_lines(file_path)
            if mime not in mime_lines:
                mime_lines[mime] = 0
            mime_lines[mime] += line_count

        mime_types.update([mt])
        if mt not in mime_sizes:
            mime_sizes[mt] = 0
        mime_sizes[mt] += f_stat.st_size

        if storage_name not in proxy:
            found_bytes += f_stat.st_size
            enter[storage_name] = (
                storage_name,
                str(line_count),
                str(f_stat.st_size),
                str(f_stat.st_ctime),
                str(f_stat.st_mtime),
                f'sha256:{storage_hash}',
                mt,
            )
        else:
            update.add(storage_name)
    return found_bytes, public, private, non_file, mime_types, mime_sizes, mime_lines


def distribute_changes(enter, leave, keep, proxy, update):
    entered_bytes, ignored_bytes, updated_bytes, left_bytes = 0, 0, 0, 0
    for k, v in proxy.items():
        if k in update:
            ignored_bytes += int(v[2])
            keep[k] = copy.deepcopy(v)
        else:
            left_bytes += int(v[2])
            leave[k] = copy.deepcopy(v)
    updated_bytes += ignored_bytes
    for k, v in enter.items():
        entered_bytes += int(v[2])
        keep[k] = copy.deepcopy(v)
    updated_bytes += entered_bytes
    return entered_bytes, ignored_bytes, left_bytes, updated_bytes


def derive_proxy_paths(start_ts):
    added_db = pathlib.Path(STORE_PATH_ENTER, f'added-{db_timestamp(start_ts)}.csv')
    proxy_db = pathlib.Path(STORE_PATH_PROXY, f'proxy-{db_timestamp(start_ts)}.csv')
    gone_db = pathlib.Path(STORE_PATH_TOMBS, f'gone-{db_timestamp(start_ts)}.csv')
    pathlib.Path(STORE_PATH_ENTER).mkdir(parents=True, exist_ok=True)
    pathlib.Path(STORE_PATH_PROXY).mkdir(parents=True, exist_ok=True)
    pathlib.Path(STORE_PATH_TOMBS).mkdir(parents=True, exist_ok=True)
    return added_db, gone_db, proxy_db


def process(tree_root):
    """Drive the tree visitor."""

    hash_policy = HASH_POLICY
    proxy_db = os.getenv(PROXY_DB, '')
    proxy_db_path = proxy_db if proxy_db else STORE_PATH_PROXY
    report = {
        'pwd': str(pathlib.Path.cwd()),
        'proxy_db_path': str(proxy_db_path),
        'store_root': str(STORE_ROOT),
    }
    try:
        proxy = load(proxy_db_path)
    except FileNotFoundError:
        proxy = {}
        print(
            f'Warning: Initializing proxy databases below {STORE_ROOT} as no path given per {PROXY_DB} or load failed'
        )

    previous = len(proxy)
    enter, update, leave = {}, set(), {}
    at_or_below = tree_root

    try:
        repo = Repo(at_or_below)
    except InvalidGitRepositoryError:
        print(f'Warning: Tree {at_or_below} is not under version control')
        repo = None
    branch_name = None
    revision = None
    revision_date = None
    origin_url = None
    if repo:
        try:
            origin_url = repo.remotes.origin.url
        except AttributeError:
            print(f'Warning: Repository {at_or_below} has no remote')
            pass
        branch_name = repo.active_branch.name
        try:
            revision = repo.head.commit
            revision_date = naive_timestamp(dti.datetime.utcfromtimestamp(revision.committed_date))
        except ValueError:
            pass

    report['origin_url'] = origin_url
    report['branch_name'] = branch_name
    report['revision_hash'] = str(revision) if revision else None
    report['revision_date'] = revision_date
    report['previous'] = str(previous)
    report['at_or_below'] = str(at_or_below)

    algorithms = None
    if hash_policy != HASH_POLICY:
        algorithms = {
            HASH_POLICY: hashlib.sha256,
        }
        print(f'Warning: Store seems to not use ({HASH_POLICY}) - using ({HASH_POLICY})')

    start_ts = dti.datetime.now()
    report['spider_start'] = naive_timestamp(start_ts)
    stream_size = spider_tree(at_or_below)
    report['visitor_start'] = naive_timestamp()
    found_bytes, public, private, non_file, mt_c, mt_s, mt_l = visit_store(
        at_or_below, hash_policy, algorithms, enter, proxy, update
    )

    keep = {}
    entered_bytes, ignored_bytes, left_bytes, updated_bytes = distribute_changes(enter, leave, keep, proxy, update)

    added_db, gone_db, proxy_db = derive_proxy_paths(start_ts)

    report['mime_file_counter'] = str(pathlib.Path(STORE_ROOT, 'mime-counts.json'))
    report['mime_size_bytes'] = str(pathlib.Path(STORE_ROOT, 'mime-sizes-bytes.json'))
    report['mime_line_counts'] = str(pathlib.Path(STORE_ROOT, 'mime-line-counts.json'))

    with open(report['mime_file_counter'], 'wt', encoding=ENCODING) as handle:
        json.dump(dict(mt_c), handle, indent=2, sort_keys=True)

    with open(report['mime_size_bytes'], 'wt', encoding=ENCODING) as handle:
        json.dump(mt_s, handle, indent=2, sort_keys=True)

    with open(report['mime_line_counts'], 'wt', encoding=ENCODING) as handle:
        json.dump(mt_l, handle, indent=2, sort_keys=True)

    entered, updated, left = len(enter), len(keep), len(leave)
    ignored = public - entered
    for db, kind in ((added_db, enter), (proxy_db, keep), (gone_db, leave)):
        archive(gen_out_stream(kind), db)

    report['entered'] = entered
    report['entered_bytes'] = entered_bytes
    report['added_db'] = str(added_db)
    report['ignored'] = ignored
    report['ignored_bytes'] = ignored_bytes
    report['updated'] = updated
    report['updated_bytes'] = updated_bytes
    report['proxy_db'] = str(proxy_db)
    report['left'] = left
    report['left_bytes'] = left_bytes
    report['gone_db'] = str(gone_db)
    report['found_bytes'] = found_bytes
    report['stream_size'] = stream_size
    report['private'] = private
    report['public'] = public
    report['non_file'] = non_file
    report['typer_stop'] = naive_timestamp()

    with open(pathlib.Path('report.json'), 'wt', encoding=ENCODING) as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    return 0


def main(argv=None):
    """LALALA."""
    argv = argv if argv else sys.argv[1:]
    if len(argv) != 1:
        print('ERROR tree root argument expected.', file=sys.stderr)
        return 2
    tree_root = argv[0].strip()
    return process(tree_root)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
