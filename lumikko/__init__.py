# [[[fill git_describe()]]]
__version__ = '2023.10.22+parent.dirty'
# [[[end]]] (checksum: 2ec7336ee3433f0f339b27afb5f776df)
__version_info__ = tuple(
    e if '-' not in e else e.split('-')[0] for part in __version__.split('+') for e in part.split('.') if e != 'parent'
)
