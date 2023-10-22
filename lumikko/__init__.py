# [[[fill git_describe()]]]
__version__ = '2023.10.22+parent.e3ae1b59'
# [[[end]]] (checksum: 53a174a641270d716ece16e3f394c406)
__version_info__ = tuple(
    e if '-' not in e else e.split('-')[0] for part in __version__.split('+') for e in part.split('.') if e != 'parent'
)
