"""
Fallback backend for platforms where parenting to Blender is not yet
supported. Widgets are made to stay on top instead.
"""
from PySide6 import QtCore


def setup(app):
    pass


def main_window_handle():
    return None


def register_main_window(widget):
    pass


def parent(widget):
    widget.setWindowFlags(widget.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    return widget
