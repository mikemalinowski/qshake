# qshake vendor folder

qshake loads PySide6 from this folder rather than from Blender's own python,
laid out as:

```
_vendor/
  general/                    # pure python modules, always on sys.path
  <platform>/<blender version>/   # e.g. windows/4.2, windows/5.1 - PySide6 builds
```

Different Blender versions need different PySide6 builds, so qshake uses the
highest version folder which is not newer than the running Blender (Blender
4.5 uses `4.2`, Blender 5.2 uses `5.1`).

## Installing PySide6

If the folder for your Blender version is missing, install it from within
Blender. In Blender's Python Console (or any script):

```python
import sys
sys.path.append(r"C:\path\to\folder\containing\qshake")  # if qshake is not already importable

import qshake
qshake.install_pyside()
```

This will:

1. Work out which folder the running Blender needs (from `VERSIONS` in
   `install_vendor.py`, e.g. Blender 4.2 -> `windows/4.2` -> PySide6 6.9.1).
2. Download PySide6 with Blender's own pip into that folder. Blender is
   unresponsive whilst this happens (typically under a minute), and pip's
   output is shown in Blender's system console (Window > Toggle System
   Console).
3. Initialise qshake, so it can be used straight away without restarting:

```python
from PySide6 import QtWidgets

window = QtWidgets.QMainWindow()
qshake.show(window)
```

`install_pyside()` returns `True` once qshake is ready. Calling it when
PySide6 is already installed does nothing, so it is safe to call from a
startup script.

### Options

```python
qshake.install_pyside(
    blender_version="5.1",    # install a specific folder rather than the one this Blender uses
    pyside_version="6.12.0",  # override the PySide6 version from VERSIONS ("latest" for the newest)
    force=True,               # reinstall even if the folder already has PySide6
)
```

`force=True` cannot replace a folder which has already been loaded in this
Blender session (Windows locks the files) - restart Blender first, and
reinstall before importing anything which uses PySide6.

### Without qshake installed

Before `qshake.install_pyside()` has been run, `import qshake` still works,
but its functions raise:

```
RuntimeError: qshake has no PySide6 build for Blender (4, 2) on windows - call qshake.install_pyside()
```

## Rebuilding every folder

To rebuild every folder listed in `VERSIONS` (for instance before
distributing qshake), run `install_vendor.py` with any Python 3.10+:

```
python qshake/install_vendor.py
python qshake/install_vendor.py windows 5.1          # a single folder
blender --background --python qshake/install_vendor.py -- windows 5.1
```
