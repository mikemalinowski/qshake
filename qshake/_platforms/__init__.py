"""
Platform specific behaviour lives in backend modules within this package.
Each backend is a plain module which exposes:

    setup(app)
        Called once when the QApplication is created.

    main_window_handle()
        Returns the native handle of Blender's main window, or None.

    parent(widget)
        Attaches a top level widget to Blender's main window.

    register_main_window(widget)
        Called once with qshake's hidden stand-in QMainWindow. Windows
        parented to it should be attached to Blender's main window.

This module must not import PySide6, as it is used to resolve which vendor
folder PySide6 is loaded from.
"""
import sys

# -- The platform name, which is also the name of the vendor folder
if sys.platform == "win32":
    NAME = "windows"

elif sys.platform == "darwin":
    NAME = "macos"

else:
    NAME = "linux"


def backend():
    """
    Returns the backend module for this platform, falling back to the
    generic backend for platforms which are not yet supported.
    """
    if NAME == "windows":
        from . import windows
        return windows

    from . import generic
    return generic
