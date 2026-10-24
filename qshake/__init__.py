"""
# qshake

## Overview
A very light weight module which allows PySide6 to be used within Blender.

PySide6 is vendored within the `_vendor` folder of this package, with a
folder per platform and Blender version (as different Blender versions need
different PySide6 builds). Importing qshake adds the right one to the path,
so `from PySide6 import QtWidgets` then works from anywhere within Blender.

If PySide6 can already be imported (a studio's own build, for instance),
that one is used instead, and nothing is added to the path or downloaded.

Because Blender owns the main event loop, qshake never calls `app.exec()`.
Instead it pumps the Qt event loop from a Blender timer.

## Getting Started Quick

```python
import qshake
from PySide6 import QtWidgets

window = QtWidgets.QMainWindow()
window.setCentralWidget(QtWidgets.QPushButton("Hello Blender"))

# -- Parents the window to Blender, shows it and keeps it alive
qshake.show(window)
```

## Platform Support
Parenting to the Blender window is supported on Windows. Platform specific
code lives in the `_platforms` package, see there for adding a platform.
"""
from . import core
from .core import (
    application,
    install_pyside,
    main_window,
    main_window_handle,
    parent,
    show,
)

# -- Create the application on import so widgets can be constructed straight
# -- away. If there is no PySide6 build, qshake.install_pyside() must be called.
core.initialise()
