from PyQt5 import QtCore
import pyqtgraph as pg

class ImageItem(pg.ImageItem):

    leftMousePressSignal = QtCore.pyqtSignal(int, int)
    rightMousePressSignal = QtCore.pyqtSignal(int, int)
    middleMousePressSignal = QtCore.pyqtSignal(int, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, ev):
        x = int(ev.pos().x())
        y = int(ev.pos().y())
        if ev.button() == QtCore.Qt.MouseButton.LeftButton:
            self.leftMousePressSignal.emit(x,y)
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.rightMousePressSignal.emit(x,y)
        if ev.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.middleMousePressSignal.emit(x,y)
