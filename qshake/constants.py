"""
Constants used by qshake. This module must not import PySide6, as the
vendor paths are needed to find the PySide6 build to load.
"""
import os

from . import _platforms

# -- How often (in seconds) the Qt event loop is pumped
TIMER_INTERVAL = 0.01

# -- The longest (in seconds) a single pump may spend processing events. Qt's
# -- event loop also dispatches the native messages of Blender's own windows,
# -- and keeps going until there are none left, which never happens if
# -- handling them creates more (as during a viewport drag). Blender's main
# -- loop is waiting on the pump meanwhile, so the pump must always end.
PUMP_TIME_LIMIT = 0.01

VENDOR_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")

# -- Pure python modules which are not platform specific
VENDOR_GENERAL = os.path.join(VENDOR_BASE, "general")

VENDOR_ROOT = os.path.join(VENDOR_BASE, _platforms.NAME)

# -- Name given to the hidden stand-in for Blender's main window
MAIN_WINDOW_OBJECT_NAME = "qshakeBlenderMainWindow"
