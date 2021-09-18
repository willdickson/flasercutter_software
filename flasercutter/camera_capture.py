import cv2
import pathlib

class CameraCapture(cv2.VideoCapture):

    MIN_EXPOSURE = 1
    MAX_EXPOSURE = 5000
    SINGLE_STEP_EXPOSURE = 10

    AUTO_EXPOSURE_ON = 3
    AUTO_EXPOSURE_OFF = 1

    DEFAULT_FRAME_WIDTH = 1280
    DEFAULT_FRAME_HEIGHT = 720
    DEFAULT_EXPOSURE = 200
    DEFAULT_AUTO_EXPOSURE = AUTO_EXPOSURE_OFF 
    

    def __init__(self, dev):
        super().__init__(dev)
        if not self.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG')):
            raise RuntimeError('unable to set fourcc to mjpg')
        if not self.set(cv2.CAP_PROP_FRAME_WIDTH, self.DEFAULT_FRAME_WIDTH):
            raise RuntimeError('unable to set frame width')
        if not self.set(cv2.CAP_PROP_FRAME_HEIGHT, self.DEFAULT_FRAME_HEIGHT):
            raise RuntimeError('unable to set frame height')
        if not self.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.DEFAULT_AUTO_EXPOSURE):
            raise RuntimeError('unable to set auto exposure')
        if not self.set_exposure(self.DEFAULT_EXPOSURE):
            raise RuntimeError('unable to set auto exposure')

    def set_auto_exposure(self,value):
        if not bool(value):
            raise ValueError('exposure value must be bool')
        if value:
            rval = self.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.AUTO_EXPOSURE_ON)
        else:
            rval = self.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.AUTO_EXPOSURE_OFF)
        return rval

    def set_exposure(self,value):
        value_clamped = min(max(value,self.MIN_EXPOSURE), self.MAX_EXPOSURE)
        rval = self.set(cv2.CAP_PROP_EXPOSURE, value_clamped)
        return rval

    @staticmethod
    def get_devices():
        path = pathlib.Path('/dev')
        files = path.glob('video*')
        return sorted([item.as_posix() for item in files])
