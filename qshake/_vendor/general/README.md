# general

Pure python modules which are not platform specific. This folder is always
added to `sys.path` when qshake is imported, after the platform/Blender
version folder (so PySide6 there takes priority over anything here).

Modules are placed here by hand, they are not managed by `install_vendor.py`.
