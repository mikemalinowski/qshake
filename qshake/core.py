"""
The QApplication, the pumping of the Qt event loop from Blender, and the
functions for parenting and showing widgets.

PySide6 is not imported at module level, as the vendor folder must be added
to the path first - initialise does both.
"""
import time
import atexit

from . import _platforms
from . import constants
from . import vendoring


class _CoreState:
    """
    Runtime state of the core module.
    """
    # -- Set by initialise once PySide6 has been imported
    backend = None
    initialised = False

    # -- Widgets shown through qshake.show are stored here to prevent them
    # -- from being garbage collected
    widgets = []

    # -- The hidden stand-in for Blender's main window, and a QWindow wrapping
    # -- Blender's native window which is used to read its geometry
    main_window = None
    blender_window = None

    # -- The native event filter which ends a pump once its time is up, and
    # -- the time (from time.perf_counter) the current pump must end by, or
    # -- None when no pump is running
    pump_limiter = None
    pump_deadline = None


def initialise():
    """
    Adds the vendor folders to the path, imports PySide6 and creates the
    application. Returns False if there is no PySide6 build for this Blender.
    """
    if not vendoring.add():
        return False

    # -- Imported before registering _shutdown, as atexit runs in reverse
    # -- order and PySide6 registers its own cleanup when first imported
    import PySide6.QtWidgets
    atexit.register(_shutdown)

    _CoreState.backend = _platforms.backend()
    application()

    _CoreState.initialised = True
    return True


def install_pyside(blender_version=None, pyside_version=None, force=False):
    """
    Installs PySide6 into the vendor folder used by this Blender version,
    then initialises qshake so it can be used straight away. Blender will be
    unresponsive whilst PySide6 downloads.

    Args:
        blender_version: The vendor folder to install (e.g. "4.2"). Defaults
            to the folder the running Blender version uses.
        pyside_version: Overrides the PySide6 version listed in
            install_vendor.VERSIONS.
        force: Reinstall even if the folder already contains PySide6.

    Returns:
        True if qshake is initialised and ready to use.
    """
    vendoring.install(blender_version, pyside_version, force)

    if not _CoreState.initialised:
        initialise()

    return _CoreState.initialised


def application():
    """
    Returns the QApplication, creating it if needed, and ensures the Qt
    event loop is being pumped by Blender.
    """
    if _CoreState.backend is None:
        _require()

    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance()

    if app is None:
        app = QtWidgets.QApplication(["blender"])
        app.setQuitOnLastWindowClosed(False)

    _CoreState.backend.setup(app)

    if _CoreState.pump_limiter is None:
        _CoreState.pump_limiter = _create_pump_limiter()
        app.installNativeEventFilter(_CoreState.pump_limiter)

    try:
        import bpy

        if not bpy.app.timers.is_registered(_pump):
            bpy.app.timers.register(_pump, persistent=True)

    except ImportError:
        pass

    return app


def main_window_handle():
    """
    Returns the native window handle of the Blender main window (an HWND on
    Windows), or None if it cannot be found or the platform is not supported.
    """
    _require()
    return _CoreState.backend.main_window_handle()


def main_window():
    """
    Returns a QMainWindow which represents the Blender main window, for use
    as the parent of any QDialog/QMainWindow (or widget with the Qt.Window
    flag). Windows parented to it behave as if passed to qshake.parent.

    It is a hidden stand-in (Blender has no QMainWindow), so it should never
    be shown itself, and plain child widgets of it will not be visible.
    """
    if _CoreState.main_window is None:
        application()

        from PySide6 import QtWidgets

        window = QtWidgets.QMainWindow()
        window.setObjectName(constants.MAIN_WINDOW_OBJECT_NAME)
        window.setWindowTitle("Blender")
        window.winId()

        _CoreState.main_window = window
        _CoreState.backend.register_main_window(window)
        _sync_main_window()

    return _CoreState.main_window


def parent(widget):
    """
    Parents the given QWidget/QMainWindow to the Blender main window. The
    widget will stay above Blender, minimise with it and will not appear
    as a separate item on the taskbar.

    The widget should not already have a Qt parent.
    """
    application()

    from PySide6 import QtCore

    if widget.parent() is None:
        widget.setWindowFlags(widget.windowFlags() | QtCore.Qt.Window)

    return _CoreState.backend.parent(widget)


def show(widget):
    """
    Parents the widget to Blender, shows it and keeps a reference to it so
    it is not garbage collected. The reference is released when the
    widget is destroyed.
    """
    parent(widget)

    if widget not in _CoreState.widgets:
        _CoreState.widgets.append(widget)
        widget.destroyed.connect(lambda *_: _forget(widget))

    widget.show()
    widget.raise_()
    widget.activateWindow()

    return widget


def _require():
    """
    Raises a RuntimeError if qshake has not been initialised, which happens
    when there is no PySide6 build for the running Blender version.
    """
    if not _CoreState.initialised:
        raise RuntimeError(
            f"qshake has no PySide6 build for Blender {vendoring.blender_version()} "
            f"on {_platforms.NAME} - call qshake.install_pyside()"
        )


def _pump():
    """
    Called by a Blender timer to process pending Qt events. Returns the
    number of seconds until the next call, or None to stop the timer once
    the QApplication no longer exists.
    """
    from PySide6 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance()

    if app is None:
        return None

    # -- Blender can run its timers while handling a native message, which
    # -- the pump itself may have dispatched, so never pump within a pump
    if _CoreState.pump_deadline is not None:
        return constants.TIMER_INTERVAL

    _sync_main_window()

    # -- The pump limiter interrupts the event loop once the deadline passes
    _CoreState.pump_deadline = time.perf_counter() + constants.PUMP_TIME_LIMIT
    try:
        app.processEvents()

    finally:
        _CoreState.pump_deadline = None

    # -- deleteLater relies on a running event loop, so flush them manually
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    return constants.TIMER_INTERVAL


def _create_pump_limiter():
    """
    Returns a native event filter which interrupts Qt's event loop once the
    current pump's deadline has passed. Qt calls it before dispatching each
    native message, and an interrupted loop stops after that message, so no
    message is lost.

    A message dispatched by the pump can start a nested native loop which
    outlasts the deadline, such as Windows' modal loop while a Qt window is
    resized. Every interrupt posts a wake-up message, and posted messages
    are retrieved before mouse input, so interrupting on every message
    would starve that loop of the mouse release which ends it. After each
    interrupt the deadline is therefore moved on by another time limit.
    """
    from PySide6 import QtCore

    class _PumpLimiter(QtCore.QAbstractNativeEventFilter):

        def nativeEventFilter(self, event_type, message):
            deadline = _CoreState.pump_deadline

            if deadline is not None:
                now = time.perf_counter()

                if now > deadline:
                    _CoreState.pump_deadline = now + constants.PUMP_TIME_LIMIT

                    dispatcher = QtCore.QAbstractEventDispatcher.instance()
                    if dispatcher is not None:
                        dispatcher.interrupt()

            return False, 0

    return _PumpLimiter()


def _sync_main_window():
    """
    Keeps the hidden main window over Blender's main window, so that dialogs
    parented to it are centred over Blender.
    """
    main = _CoreState.main_window

    if main is None:
        return

    handle = main_window_handle()

    if not handle:
        return

    from PySide6 import QtGui

    if _CoreState.blender_window is None or _CoreState.blender_window.winId() != handle:
        _CoreState.blender_window = QtGui.QWindow.fromWinId(handle)

    # -- QWidget.setGeometry does not move the native window whilst hidden,
    # -- and the QWindow only updates the QWidget once events are processed,
    # -- so both are set (dialogs centre using the QWidget's size)
    geometry = _CoreState.blender_window.geometry()
    window = main.windowHandle()

    # -- The first move of the never-shown native window lands slightly off
    # -- (by the frame margins), so it is set a second time if needed
    for _ in range(2):
        if main.geometry() == geometry and window.geometry() == geometry:
            break

        main.setGeometry(geometry)
        window.setGeometry(geometry)


def _forget(widget):
    """
    Releases the reference qshake.show holds to the given widget, once
    it has been destroyed.
    """
    if widget in _CoreState.widgets:
        _CoreState.widgets.remove(widget)


def _shutdown():
    """
    Called when Python exits, to close any widgets which are still open
    (those shown through qshake.show and those parented to the main
    window) before PySide6 deletes them.
    """
    from PySide6 import QtWidgets

    widgets = list(_CoreState.widgets)

    if _CoreState.main_window is not None:
        widgets.extend(
            child
            for child in _CoreState.main_window.findChildren(QtWidgets.QWidget)
            if child.isWindow()
        )

    for widget in widgets:
        try:
            widget.close()
        except RuntimeError:
            pass

    _CoreState.widgets.clear()
