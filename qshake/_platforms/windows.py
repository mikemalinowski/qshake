"""
Windows backend. Widgets are parented by making the Blender main window
the Win32 owner of the widget's native window, which keeps the widget above
Blender, minimises it with Blender and removes its taskbar entry.
"""
import os
import ctypes
from ctypes import wintypes

from PySide6 import QtCore

from . import generic

# -- The values below are copied from the Windows SDK's WinUser.h, as ctypes
# -- cannot read C headers. They are fixed IDs, so they must match exactly.

# -- GetWindow command which returns a window's owner (GW_OWNER)
_GW_OWNER = 4

# -- SetWindowLongPtr index which, for a top level window, sets its owner
# -- (despite the name, it is the owner rather than the parent)
_GWLP_HWNDPARENT = -8

# -- Sent when a window is being destroyed, used to stop tracking it
_WM_DESTROY = 0x0002

# -- Sent just before a window is shown or hidden (wParam is non-zero when
# -- showing), which is the point where the owner is re-applied
_WM_SHOWWINDOW = 0x0018



class _WindowsState:
    """
    Runtime state of the Windows backend.
    """
    # -- Private ctypes instance of user32.dll, created on first use by _user32
    user32 = None

    # -- The native event filter installed on the QApplication by setup
    filter = None

    # -- Cached HWND of Blender's main window, re-found if it becomes invalid
    blender_hwnd = None

    # -- Native handle of qshake's hidden stand-in main window
    main_window_hwnd = None

    # -- Native handles of the windows which should be owned by Blender
    owned = set()


def setup(app):
    if _WindowsState.filter is None:
        _WindowsState.filter = _OwnerFilter()
        app.installNativeEventFilter(_WindowsState.filter)


def main_window_handle():
    """
    Returns the HWND of the Blender main window, or None if it cannot be found.
    """
    user32 = _user32()

    if _WindowsState.blender_hwnd and user32.IsWindow(_WindowsState.blender_hwnd):
        return _WindowsState.blender_hwnd

    pid = os.getpid()
    owned = []
    unowned = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _visit(hwnd, _):
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

        if window_pid.value != pid or not user32.IsWindowVisible(hwnd):
            return True

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)

        if class_name.value == "GHOST_WindowClass":

            # -- Blender's secondary windows (preferences etc) are owned
            # -- by the main window, so prefer those without an owner
            if user32.GetWindow(hwnd, _GW_OWNER):
                owned.append(hwnd)
            else:
                unowned.append(hwnd)

        return True

    user32.EnumWindows(_visit, 0)

    candidates = unowned + owned
    _WindowsState.blender_hwnd = candidates[0] if candidates else None

    return _WindowsState.blender_hwnd


def parent(widget):
    hwnd = main_window_handle()

    if hwnd is None:
        return generic.parent(widget)

    # -- Qt does not apply transient parents which are foreign windows, and
    # -- clears the owner every time the window is shown. Therefore we set the
    # -- owner directly, and the native event filter re-applies it just before
    # -- the window becomes visible.
    widget_hwnd = int(widget.winId())
    _WindowsState.owned.add(widget_hwnd)
    _set_owner(widget_hwnd, hwnd)

    return widget


def register_main_window(widget):
    """
    Qt makes windows parented to the stand-in main window owned by it, so the
    native event filter hands those over to Blender when they are shown.
    """
    _WindowsState.main_window_hwnd = int(widget.winId())


def _set_owner(window_hwnd, hwnd):
    if not hwnd:
        return

    user32 = _user32()

    if user32.GetWindow(window_hwnd, _GW_OWNER) != hwnd:
        user32.SetWindowLongPtrW(window_hwnd, _GWLP_HWNDPARENT, hwnd)


class _OwnerFilter(QtCore.QAbstractNativeEventFilter):
    """
    WM_SHOWWINDOW is sent after Qt has cleared the owner but before the
    window becomes visible, so this is where the owner is re-applied.
    """

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))

        if msg.message == _WM_SHOWWINDOW and msg.wParam:
            if msg.hWnd in _WindowsState.owned or self._owned_by_main_window(msg.hWnd):
                _set_owner(msg.hWnd, main_window_handle())

        elif msg.message == _WM_DESTROY:
            _WindowsState.owned.discard(msg.hWnd)

        return False, 0

    @staticmethod
    def _owned_by_main_window(hwnd):
        if not _WindowsState.main_window_hwnd:
            return False

        return _user32().GetWindow(hwnd, _GW_OWNER) == _WindowsState.main_window_hwnd


def _user32():
    """
    Returns a private user32 instance so that defining argtypes here does
    not affect any other code using ctypes.windll.user32
    """
    if _WindowsState.user32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetWindow.restype = wintypes.HWND
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p

        _WindowsState.user32 = user32

    return _WindowsState.user32
