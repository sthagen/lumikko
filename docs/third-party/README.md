# Third Party Dependencies

<!--[[[fill sbom_sha256()]]]-->
The [SBOM in CycloneDX v1.4 JSON format](https://git.sr.ht/~sthagen/lumikko/blob/default/sbom.json) with SHA256 checksum ([7c3b8e18 ...](https://git.sr.ht/~sthagen/lumikko/blob/default/sbom.json.sha256 "sha256:7c3b8e18fdd156adb1de0924643a4b1dbb0d6720cf7d1bfa52cefadec11a7ac3")).
<!--[[[end]]] (checksum: 0698a63ea79c1a080080313bb5ff0f4e)-->
## Licenses 

JSON files with complete license info of: [direct dependencies](direct-dependency-licenses.json) | [all dependencies](all-dependency-licenses.json)

### Direct Dependencies

<!--[[[fill direct_dependencies_table()]]]-->
| Name                                                           | Version                                              | License     | Author                         | Description (from packaging data)                                    |
|:---------------------------------------------------------------|:-----------------------------------------------------|:------------|:-------------------------------|:---------------------------------------------------------------------|
| [GitPython](https://github.com/gitpython-developers/GitPython) | [3.1.30](https://pypi.org/project/GitPython/3.1.30/) | BSD License | Sebastian Thiel, Michael Trier | GitPython is a python library used to interact with Git repositories |
<!--[[[end]]] (checksum: 4f2d680028b2c44561176506c5d13e29)-->

### Indirect Dependencies

<!--[[[fill indirect_dependencies_table()]]]-->
| Name                                                   | Version                                          | License     | Author          | Description (from packaging data)                                   |
|:-------------------------------------------------------|:-------------------------------------------------|:------------|:----------------|:--------------------------------------------------------------------|
| [gitdb](https://github.com/gitpython-developers/gitdb) | [4.0.10](https://pypi.org/project/gitdb/4.0.10/) | BSD License | Sebastian Thiel | Git Object Database                                                 |
| [smmap](https://github.com/gitpython-developers/smmap) | [5.0.0](https://pypi.org/project/smmap/5.0.0/)   | BSD License | Sebastian Thiel | A pure Python implementation of a sliding window memory map manager |
<!--[[[end]]] (checksum: f03261aff3e39e81702abf0193a194dd)-->

## Dependency Tree(s)

JSON file with the complete package dependency tree info of: [the full dependency tree](package-dependency-tree.json)

### Rendered SVG

Base graphviz file in dot format: [Trees of the direct dependencies](package-dependency-tree.dot.txt)

<img src="./package-dependency-tree.svg" alt="Trees of the direct dependencies" title="Trees of the direct dependencies"/>

### Console Representation

<!--[[[fill dependency_tree_console_text()]]]-->
````console
GitPython==3.1.30
  - gitdb [required: >=4.0.1,<5, installed: 4.0.10]
    - smmap [required: >=3.0.1,<6, installed: 5.0.0]
````
<!--[[[end]]] (checksum: ea1abf1b9bfcc6dc06232cdeb89d8075)-->
