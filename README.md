# qshake

A very light weight module which allows PySide6 to be used within Blender.
PySide6 lives in a vendor folder inside the package (one build per platform
and Blender version), so nothing is installed into Blender's own python.

## Setup

1. Make the folder containing the `qshake` package importable in Blender, for
   instance by adding it to `sys.path` or placing it in Blender's
   `scripts/modules` folder.

2. If the vendor folder for your Blender version is not already present,
   install PySide6 from within Blender (e.g. in the Python Console):

   ```python
   import qshake
   qshake.install_pyside()
   ```

   This downloads PySide6 with Blender's own pip into
   `_vendor/<platform>/<blender version>` and initialises qshake, so it can be
   used straight away without restarting. Blender is unresponsive whilst it
   downloads (pip's output is shown in Window > Toggle System Console).

`install_pyside()` does nothing if PySide6 is already installed, so it is safe
to call from a startup script. Until it has been run, `import qshake` still
works but qshake's functions raise an error pointing at `install_pyside()`.
See `qshake/_vendor/README.md` for more detail.

## Usage

```python
import qshake
from PySide6 import QtWidgets

window = QtWidgets.QMainWindow()
window.setCentralWidget(QtWidgets.QPushButton("Hello Blender"))

# -- Parents the window to Blender, shows it and keeps it alive
qshake.show(window)
```

| Function | Description |
| --- | --- |
| `qshake.show(widget)` | Parents to Blender, shows, and keeps a reference until the widget is destroyed |
| `qshake.parent(widget)` | Parents to Blender without showing |
| `qshake.main_window()` | Returns a QMainWindow representing Blender, to pass as a `parent` |
| `qshake.application()` | Returns the QApplication (created automatically on import) |
| `qshake.main_window_handle()` | Returns Blender's native main window handle (HWND on Windows) |
| `qshake.install_pyside(blender_version=None, pyside_version=None, force=False)` | Installs PySide6 for this Blender and initialises qshake |

Parented windows stay above Blender, minimise with it and do not get their
own taskbar entry. Call `parent`/`show` after setting any window flags, as
changing flags recreates the native window.

### Passing Blender as a parent

Code which expects a parent main window can be given `qshake.main_window()`:

```python
dialog = MyDialog(parent=qshake.main_window())
dialog.show()
```

Blender has no QMainWindow, so this is a hidden stand-in which qshake keeps
positioned over Blender. Windows parented to it (`QDialog`, `QMainWindow`, or
anything with the `Qt.Window` flag) behave as if passed to `qshake.parent`,
are centred over Blender, and are kept alive by Qt's parenting. Note that:

- It should never be shown itself.
- Plain child widgets of it (without `Qt.Window`) will not be visible.
- `QDialog.exec()` blocks Blender until the dialog closes, as Blender's UI
  shares the thread. Prefer `show()` or `open()`.

## Package Layout

```
qshake/
  __init__.py           # vendor selection, QApplication, event pump, public functions
  install_vendor.py     # builds the vendor folders (used by install_pyside)
  _platforms/           # platform specific code, see Platforms below
    __init__.py
    windows.py
    generic.py
  _vendor/
    general/            # pure python modules, always on sys.path
    windows/<version>/  # PySide6 builds, one per Blender version
```

## Vendor Folders

PySide6 binaries are platform specific, and different Blender versions need
different PySide6 builds, so `_vendor` is laid out as
`_vendor/<platform>/<blender version>`. qshake uses the highest folder which
is not newer than the running Blender (so 4.5 uses `4.2`, 5.2 uses `5.1`),
and the newest when imported outside of Blender.

The versions installed for each folder are listed in `VERSIONS` in
`install_vendor.py`:

| Folder | PySide6 | Notes |
| --- | --- | --- |
| `windows/4.2` | 6.9.1 | Newer builds crash against Blender 4.x's older MSVC runtime |
| `windows/5.1` | 6.12.0 | |

Adding a Blender version only needs a new entry in `VERSIONS`; no other code
changes are needed.

`_vendor/general` holds pure python modules which are not platform specific.
It is always added to `sys.path` (after the platform folder, so PySide6 there
takes priority) and is maintained by hand rather than by `install_vendor.py`.

### Rebuilding the folders

`install_vendor.py` can rebuild the folders outside of Blender, for instance
before distributing qshake with the binaries included. It runs with any
Python 3.10+:

```
python qshake/install_vendor.py                        # every folder in VERSIONS
python qshake/install_vendor.py windows 5.1            # a single folder
python qshake/install_vendor.py windows 5.1 latest     # a single folder with a specific version
```

When running it through Blender, pass arguments after `--`:

```
blender --background --python qshake/install_vendor.py -- windows 5.1
```

A folder cannot be rebuilt whilst a Blender session has it loaded, as Windows
locks the files.

## Notes

- Blender owns the event loop, so never call `app.exec()`. qshake pumps Qt from
  a `bpy.app.timers` callback (`qshake.constants.TIMER_INTERVAL`, default 10ms).
- Qt prints a harmless `SetProcessDpiAwarenessContext() failed` warning on
  startup, as Blender has already set the process DPI awareness.

## Platforms

Platform specific code lives in `qshake/_platforms`, one module per platform,
each exposing:

| Function | Description |
| --- | --- |
| `setup(app)` | Called once when the QApplication is created |
| `main_window_handle()` | Returns the native handle of Blender's main window, or None |
| `parent(widget)` | Attaches a top level widget to Blender's main window |
| `register_main_window(widget)` | Called with the `main_window()` stand-in; windows parented to it should be attached to Blender |

Only Windows is supported currently. On other platforms `generic.py` is used,
which sets widgets to stay on top (although there are no vendor builds for
other platforms yet).

To add a platform (e.g. Linux):

1. Add `_platforms/linux.py` implementing the four functions and return it
   from `_platforms.backend()`.
2. Add the pip platform tag to `PIP_PLATFORMS` and the versions to `VERSIONS`
   in `install_vendor.py`. `install_pyside()` (or `install_vendor.py`) will
   then build `_vendor/linux/...`.
