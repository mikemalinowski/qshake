"""
Populates the qshake/_vendor/<platform>/<blender version> folders with PySide6.

Within Blender, the simplest way to use this is `qshake.install_pyside()`,
which installs the folder for the running Blender version. This script is a
maintenance tool for rebuilding the folders, which ship with qshake.

PySide6 wheels are built against the stable python ABI, so this can be run
with any Python 3.10+. Wheels are requested for the target platform, so a
platform's folders can be built from any operating system.

    python install_vendor.py                       # rebuild every folder in VERSIONS
    python install_vendor.py windows 5.1           # rebuild one folder
    python install_vendor.py windows 5.1 latest    # rebuild one folder with a specific version

When running through Blender, pass arguments after "--":

    blender --background --python install_vendor.py -- windows 5.1
"""
import os
import sys
import shutil
import subprocess

# -- Essentials contains QtCore, QtGui, QtWidgets etc without the very large
# -- add-on modules (WebEngine, 3D, Multimedia...)
PACKAGE = "PySide6-Essentials"

# -- Platform folder -> pip platform tag
PIP_PLATFORMS = {
    "windows": "win_amd64",
}

# -- Platform folder -> Blender version folder -> PySide6 version
VERSIONS = {
    "windows": {
        # -- PySide6 6.9.2+ is built with MSVC 14.40+, which crashes (std::mutex)
        # -- when run against the older msvcp140.dll that Blender 4.x ships with
        "4.2": "6.9.1",
        "5.1": "6.12.0",
    },
}


def vendor_folder():
    """
    Returns the qshake/_vendor folder. Raises if it cannot be resolved, so
    that nothing is ever written outside of the qshake package.
    """
    candidates = [os.path.dirname(os.path.abspath(__file__))]

    # -- When run from Blender's text editor __file__ is not the script's
    # -- location, but the text block's filepath is
    try:
        import bpy
        text = getattr(bpy.context.space_data, "text", None)

        if text and text.filepath:
            candidates.append(os.path.dirname(bpy.path.abspath(text.filepath)))

    except ImportError:
        pass

    for folder in candidates:
        if os.path.isfile(os.path.join(folder, "_platforms", "__init__.py")):
            return os.path.join(folder, "_vendor")

    raise RuntimeError(f"Could not find the qshake package folder from {candidates}")


def install(platform, blender_version, pyside_version=None):
    pyside_version = pyside_version or VERSIONS[platform][blender_version]
    target = os.path.join(vendor_folder(), platform, blender_version)

    # -- Windows locks loaded DLLs, so deleting a folder which is in use would
    # -- fail part way through
    loaded = sys.modules.get("PySide6")

    if loaded and _is_within(loaded.__file__, target):
        raise RuntimeError(
            f"PySide6 is loaded from {target} - restart Blender before reinstalling it"
        )

    if os.path.isdir(target):
        shutil.rmtree(target)

    if pyside_version == "latest":
        requirement = PACKAGE
    else:
        requirement = f"{PACKAGE}=={pyside_version}"

    subprocess.check_call(
        [
            sys.executable, "-m", "pip", "install",
            "--target", target,
            "--platform", PIP_PLATFORMS[platform],
            "--only-binary=:all:",
            "--no-compile",
            requirement,
        ]
    )

    # -- pip --target writes console script wrappers which are not needed
    shutil.rmtree(os.path.join(target, "bin"), ignore_errors=True)


def _is_within(path, folder):
    path = os.path.normcase(os.path.abspath(path))
    folder = os.path.normcase(os.path.abspath(folder))

    return path.startswith(folder + os.sep)


def _arguments():
    """
    Returns the script arguments, ignoring Blender's own command line
    arguments when run through Blender.
    """
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]

    try:
        import bpy
        return []

    except ImportError:
        return sys.argv[1:]


if __name__ == "__main__":
    arguments = _arguments()

    if len(arguments) > 1:
        install(arguments[0], arguments[1], arguments[2] if len(arguments) > 2 else None)

    else:
        for platform, versions in VERSIONS.items():
            for blender_version in versions:
                install(platform, blender_version)
