import cv2
import pathlib

class CameraCapture(cv2.VideoCapture):

    def __init__(self, dev):
        super().__init__(dev)
        if not self.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG')):
            raise RuntimeError('unable to set fourcc to mjpg')
        if not self.set(cv2.CAP_PROP_FRAME_WIDTH, 1280):
            raise RuntimeError('unable to set frame width')
        if not self.set(cv2.CAP_PROP_FRAME_HEIGHT, 720):
            raise RuntimeError('unable to set frame height')
        if not self.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3):
            raise RuntimeError('unable to set auto exposure')

    @staticmethod
    def get_devices():
        path = pathlib.Path('/dev')
        files = path.glob('video*')
        return sorted([item.as_posix() for item in files])
