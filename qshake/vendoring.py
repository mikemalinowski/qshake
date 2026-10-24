"""
Resolves, installs and loads the vendored PySide6 build for the running
Blender version.

This module must not import PySide6, as it is used to find the build to load.
"""
import os
import sys

from . import _platforms
from . import constants

class _VendorState:
    """
    Runtime state of the vendoring module.
    """
    # -- Handles returned from os.add_dll_directory must be kept alive
    dll_handles = []

    # -- The vendor folder PySide6 is loaded from, set by add
    folder = None


def blender_version():
    """
    Returns the running Blender version as (major, minor), or None when
    running outside of Blender.
    """
    try:
        import bpy
        return tuple(bpy.app.version[:2])

    except ImportError:
        return None


def _best_version(names, blender):
    """
    Returns the highest of the given version names (e.g. "4.2") which is not
    newer than the given Blender version, or the newest if Blender is None.
    """
    for version, name in sorted(
        ((tuple(int(n) for n in name.split(".")), name) for name in names),
        reverse=True,
    ):
        if blender is None or version <= blender:
            return name

    return None


def _vendor_folder():
    """
    Returns the vendor folder for the running Blender version, or None if
    there is no PySide6 build for it.
    """
    if not os.path.isdir(constants.VENDOR_ROOT):
        return None

    name = _best_version(
        [
            name for name in os.listdir(constants.VENDOR_ROOT)
            if os.path.isdir(os.path.join(constants.VENDOR_ROOT, name, "PySide6"))
        ],
        blender_version(),
    )

    return os.path.join(constants.VENDOR_ROOT, name) if name else None


def add():
    """
    Adds the vendor folders for the running Blender version to the path, so
    PySide6 can be imported. Returns False if there is no PySide6 build for it.
    """
    _VendorState.folder = _vendor_folder()

    if not _VendorState.folder:
        return False

    # -- The platform folder goes first, so it takes priority over general
    for path in reversed((_VendorState.folder, constants.VENDOR_GENERAL)):
        if path not in sys.path:
            sys.path.insert(0, path)

    if sys.platform == "win32":
        for name in ("shiboken6", "PySide6"):
            path = os.path.join(_VendorState.folder, name)
            if os.path.isdir(path):
                _VendorState.dll_handles.append(os.add_dll_directory(path))

    return True


def install(version=None, pyside_version=None, force=False):
    """
    Installs PySide6 into the given vendor folder (e.g. "4.2"), defaulting to
    the one used by this Blender version. See qshake.install_pyside.
    """
    from . import install_vendor

    if version is None:
        version = _best_version(
            install_vendor.VERSIONS.get(_platforms.NAME, {}), blender_version(),
        )

        if version is None:
            raise RuntimeError(
                f"qshake lists no PySide6 version for Blender {blender_version()} "
                f"on {_platforms.NAME}"
            )

    target = os.path.join(constants.VENDOR_ROOT, version)

    if force or not os.path.isdir(os.path.join(target, "PySide6")):
        install_vendor.install(_platforms.NAME, version, pyside_version)
