from __future__ import print_function
import os
import sys
import time
import functools
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources


import cv2
import serial.tools.list_ports

from PyQt5 import QtCore
from PyQt5 import QtGui 
from PyQt5 import QtWidgets
from PyQt5 import uic
import pyqtgraph as pg

from . import image_item
from . import grbl_sender
from . import calibration
from . import camera_capture


class AppMainWindow(QtWidgets.QMainWindow):

    UI_FILENAME = 'flasercutter.ui'
    CONFIG_DIRECTORY = os.path.join(os.environ['HOME'],'.config','flasercutter')

    CALIBRATION_FILENAME = 'calibration.pkl'
    CALIBRATION_MINIMUM_POINTS = 4

    CAMERA_TIMER_PERIOD = 1.0/30.0

    GRBL_TIMER_PERIOD = 1.0/100.0
    GRBL_STATUS_PERIOD = 1.0/5.0
    GRBL_DEFAULT_FEEDRATE = 3.0

    JOG_DEFAULT_XY_STEP = 0.2
    JOG_DEFAULT_Z_STEP = 0.002

    CAL_DEFAULT_PATTERN_WIDTH = 0.2
    CAL_DEFAULT_PATTERN_HEIGHT = 0.2

    IMAGE_LINE_COLOR = (0,0,255)
    IMAGE_LINE_THICKNESS =2
    IMAGE_POINT_COLOR = (0,0,255)
    IMAGE_POINT_SIZE = 6


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with pkg_resources.path(__package__, self.UI_FILENAME) as p:
            uic.loadUi(p, self)

        # Grbl 
        self.grbl = None
        self.grbl_timer = None
        self.grbl_timer_counter = 0
        self.grbl_last_status = time.time()
        self.wpos = None

        # Camera 
        self.camera = None
        self.camera_timer = None
        self.camera_running = False
        self.camera_timer_counter = 0
        self.current_image = None

        # Point list for cutting and calibrating 
        self.point_list = []

        # Calibration data
        self.calibration = calibration.Calibration() 

        self.initialize()
        self.connectActions()

    @property
    def calibration_file_fullpath(self):
        return os.path.join(self.CONFIG_DIRECTORY, self.CALIBRATION_FILENAME)

    def initialize(self):
        self.cameraStartStopPushButton.setText('Start')
        self.cameraDeviceComboBox.addItems(camera_capture.CameraCapture.get_devices())
        self.camera_timer = QtCore.QTimer()
        self.cameraExposureSpinBox.setMinimum(camera_capture.CameraCapture.MIN_EXPOSURE)
        self.cameraExposureSpinBox.setMaximum(camera_capture.CameraCapture.MAX_EXPOSURE)
        self.cameraExposureSpinBox.setValue(camera_capture.CameraCapture.DEFAULT_EXPOSURE)
        self.cameraExposureSpinBox.setEnabled(False)
        self.setCameraFrameCountLabel(0)

        self.grblConnectPushButton.setText('Connect')
        self.grblDeviceComboBox.addItems(get_usbserial_devices())
        self.grbl_timer = QtCore.QTimer()
        self.grbl_timer.start(int(convert_sec_to_msec(self.GRBL_TIMER_PERIOD)))

        self.jogStepXYDoubleSpinBox.setMinimum(self.jogStepXYDoubleSpinBox.singleStep())
        self.jogStepXYDoubleSpinBox.setValue(self.JOG_DEFAULT_XY_STEP)  
        self.jogStepZDoubleSpinBox.setMinimum(self.jogStepZDoubleSpinBox.singleStep())
        self.jogStepZDoubleSpinBox.setValue(self.JOG_DEFAULT_Z_STEP)  
        self.jogFeedrateDoubleSpinBox.setMinimum(self.jogFeedrateDoubleSpinBox.singleStep())
        self.jogFeedrateDoubleSpinBox.setValue(self.GRBL_DEFAULT_FEEDRATE)

        self.calLaserFeedrateDoubleSpinBox.setValue(self.GRBL_DEFAULT_FEEDRATE)
        self.calPatternWidthDoubleSpinBox.setValue(self.CAL_DEFAULT_PATTERN_WIDTH)
        self.calPatternHeightDoubleSpinBox.setValue(self.CAL_DEFAULT_PATTERN_HEIGHT)

        self.cutLaserFeedrateDoubleSpinBox.setValue(self.GRBL_DEFAULT_FEEDRATE)

        self.cameraView.ui.histogram.hide()
        self.cameraView.ui.roiBtn.hide()
        self.cameraView.ui.menuBtn.hide()
        self.imageItem = image_item.ImageItem(axisOrder='row-major')
        self.cameraView.addItem(self.imageItem)

        os.makedirs(self.CONFIG_DIRECTORY, exist_ok=True)
        cal_ok, cal_msg = self.calibration.load(self.calibration_file_fullpath)
        if cal_ok:
            info_str = f'{self.CALIBRATION_FILENAME} loaded'
            self.calInfoPlainTextEdit.appendPlainText(info_str)
        else:
            info_str = f'calibration not found\n'
            self.calInfoPlainTextEdit.appendPlainText(info_str)
            self.calInfoPlainTextEdit.appendPlainText(cal_msg)

        self.widgets_to_disable_on_run = [
                self.connectTab, 
                self.controlTab, 
                self.calPatternGroupBox, 
                self.calLaserGroupBox,
                self.calDataPointsGroupBox,
                self.cutGroupBox,
                ]

    def connectActions(self):
        self.stopPushButton.clicked.connect(self.onStopPushButtonClicked)
        self.gotoZeroPushButton.clicked.connect(self.onGotoZeroButtonClicked)
        self.clearPointsPushButton.clicked.connect(self.onClearPointsClicked)

        self.cameraStartStopPushButton.clicked.connect(self.onCameraStartStopButtonClicked)
        self.camera_timer.timeout.connect(self.onCameraTimer)
        self.cameraExposureSpinBox.valueChanged.connect(self.onCameraExposureChanged)

        self.grblConnectPushButton.clicked.connect(self.onGrblConnectButtonClicked)
        self.grblRefreshPushButton.clicked.connect(self.onGrblRefreshButtonClicked)
        self.grbl_timer.timeout.connect(self.onGrblTimer)

        self.laserEnableCheckBox.stateChanged.connect(self.onLaserEnableChanged)
        self.laserPowerSlider.valueChanged.connect(self.onLaserPowerChanged)
        self.cutClearPushButton.clicked.connect(self.onClearButtonClicked)

        self.jogNegPosXYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked, -1,  1,  0)
                )
        self.jogPosPosXYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  1,  1,  0)
                )
        self.jogPosNegXYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  1, -1,  0)
                )
        self.jogNegNegXYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked, -1, -1,  0)
                )
        self.jogPosXPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  1,  0,  0)
                )
        self.jogNegXPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked, -1,  0,  0)
                )
        self.jogPosYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  0,  1,  0)
                )
        self.jogNegYPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  0, -1,  0)
                )
        self.jogPosZPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  0,  0,  1)
                )
        self.jogNegZPushButton.clicked.connect(
                functools.partial(self.onJogPushButtonClicked,  0,  0, -1)
                )

        self.controlSetZeroPushButton.clicked.connect(self.onControlSetZeroButtonClicked)
        self.controlClearZeroPushButton.clicked.connect(self.onControlClearZeroButtonClicked)

        self.calLaserRunPushButton.clicked.connect(self.onCalLaserRunButtonClicked)
        self.calAcceptDataPointsPushButton.clicked.connect(self.onCalAcceptDataPointsButtonClicked)
        self.calSaveDataPointsPushButton.clicked.connect(self.onCalSaveDataPointsButtonClicked)
        self.calClearDataPointsPushButton.clicked.connect(self.onCalClearDataPointsButtonClicked)

        self.cutRunPushButton.clicked.connect(self.onCutRunButtonClicked)
        self.cutClearPushButton.clicked.connect(self.onCutClearButtonClicked)

        self.imageItem.leftMousePressSignal.connect(self.onImageLeftMouseClick)
        self.imageItem.rightMousePressSignal.connect(self.onImageRightMouseClick)
        self.imageItem.middleMousePressSignal.connect(self.onImageMiddleMouseClick)

    def onClearPointsClicked(self):
        self.point_list = []

    def onStopPushButtonClicked(self):
        if self.grbl:
            self.grbl.soft_stop()

    def onCameraStartStopButtonClicked(self):
        if not self.camera_running:
            device = self.cameraDeviceComboBox.currentText()
            self.camera = camera_capture.CameraCapture(device)
            self.camera_running = True
            self.camera_timer_counter = 0
            self.camera_timer.start(int(convert_sec_to_msec(self.CAMERA_TIMER_PERIOD)))
            self.cameraStartStopPushButton.setText('Stop')
            self.cameraExposureSpinBox.setEnabled(True)
        else:
            self.camera.release()
            self.camera_running = False
            self.camera_timer.stop()
            self.cameraStartStopPushButton.setText('Start')
            self.cameraExposureSpinBox.setEnabled(False)

    def onCameraExposureChanged(self,value):
        rval = self.camera.set_exposure(value)

    def onCameraTimer(self):
        ok, img_bgr = self.camera.read()
        if ok:
            self.current_image = img_bgr
            self.update_image()
            self.camera_timer_counter += 1
            self.setCameraFrameCountLabel(self.camera_timer_counter)

    def update_image(self): 
        img_bgr = self.current_image.copy()
        sending = False
        if self.grbl:
            sending = self.grbl.sending

        if not sending and self.pointsVisibleCheckBox.isChecked():
            for p in self.point_list:
                img_bgr = cv2.circle(img_bgr, p, self.IMAGE_POINT_SIZE, self.IMAGE_POINT_COLOR, cv2.FILLED)
            for p, q in zip(self.point_list[:-1], self.point_list[1:]):
                img_bgr = cv2.line(img_bgr, p, q, self.IMAGE_LINE_COLOR,self.IMAGE_LINE_THICKNESS)
        if self.calibration.ok:
            cx, cy = self.calibration.laser_pos_px
            cx = int(cx)
            cy = int(cy)
            sz = 10
            img_bgr = cv2.line(img_bgr, (cx-sz,cy), (cx+sz,cy), (255,255,255), 2)
            img_bgr = cv2.line(img_bgr, (cx,cy-sz), (cx,cy+sz), (255,255,255), 2)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self.imageItem.setImage(img_rgb)

    def setCameraFrameCountLabel(self,value):
        self.cameraFrameCountLabel.setText(f'Frame count: {self.camera_timer_counter}')

    def onGrblConnectButtonClicked(self):
        if self.grbl is None and self.grblDeviceComboBox.count()>0:
            device = self.grblDeviceComboBox.currentText()
            self.grbl = grbl_sender.GrblSender(port=device)
            self.grblConnectPushButton.setText('Diconnect')
            self.grblRefreshPushButton.setEnabled(False)
        else:
            self.grbl.close()
            self.grbl = None
            self.grblConnectPushButton.setText('Connect')
            self.grblRefreshPushButton.setEnabled(True)

    def onGrblRefreshButtonClicked(self):
        self.grblDeviceComboBox.addItems(get_usbserial_devices())

    def onGrblTimer(self):
        self.grbl_timer_counter += 1
        now = time.time()
        if self.grbl:
            query_status = False
            if now - self.grbl_last_status > self.GRBL_STATUS_PERIOD:
                self.grbl_last_status = now
                query_status = True
            rsp = self.grbl.update(query_status=query_status)
            if 'status' in rsp:
                self.wpos = rsp['status']['WPos']
                self.modeLabel.setText(rsp['status']['mode'])
                x = rm_negative_zero(rsp['status']['WPos']['x'])
                y = rm_negative_zero(rsp['status']['WPos']['y'])
                z = rm_negative_zero(rsp['status']['WPos']['z'])
                x_str = f"{x:1.3f}".rjust(6,' ')
                y_str = f"{y:1.3f}".rjust(6,' ')
                z_str = f"{z:1.3f}".rjust(6,' ')
                self.xLcdNumber.display(x_str)
                self.yLcdNumber.display(y_str)
                self.zLcdNumber.display(z_str)
            if not self.grbl.sending:
                self.reenable_widgets()

    def onJogPushButtonClicked(self, x_sign, y_sign, z_sign):
        xy_step_size = self.jogStepXYDoubleSpinBox.value()
        z_step_size = self.jogStepZDoubleSpinBox.value()
        feedrate = self.jogFeedrateDoubleSpinBox.value()
        if self.grbl:
            self.grbl.append_cmd('G91')
            jog_cmd = f'F{feedrate:1.2f} G1 '
            if x_sign:
                x_step = x_sign*xy_step_size
                jog_cmd = f'{jog_cmd} X{x_step:0.4f}'
            if y_sign:
                y_step = y_sign*xy_step_size 
                jog_cmd = f'{jog_cmd} Y{y_step:0.4f}'
            if z_sign:
                z_step = z_sign*z_step_size
                jog_cmd = f'{jog_cmd} Z{z_step:0.4f}'
            jog_cmd = f'{jog_cmd}'
            self.grbl.append_cmd(jog_cmd)
            self.grbl.append_cmd('G90')

    def onLaserPowerChanged(self, value):
        if self.laserEnableCheckBox.checkState() == QtCore.Qt.CheckState.Checked:
            laser_power = self.get_laser_power()
            cmd = ['M3', f'S {laser_power}']
            self.grbl.send_gcode(cmd)

    def onLaserEnableChanged(self, state):
        if state == QtCore.Qt.CheckState.Unchecked:
            cmd = ['M5']
            self.laserPowerSlider.setEnabled(True)
        else:
            laser_power = self.get_laser_power()
            cmd = ['M3', f'S {laser_power}']
            self.laserPowerSlider.setEnabled(False)
        self.grbl.send_gcode(cmd)

    def get_laser_power(self): 
        percent = self.laserPowerSlider.value()
        return percent_to_laser_power(percent)

    def onControlSetZeroButtonClicked(self):
        if self.grbl:
            self.grbl.set_zero()

    def onControlClearZeroButtonClicked(self):
        if self.grbl:
            self.grbl.clear_zero()

    def onGotoZeroButtonClicked(self):
        feedrate = self.jogFeedrateDoubleSpinBox.value()
        cmd_list = []
        cmd_list.append(f'G90')
        cmd_list.append(f'G1 X0 Y0 Z0')
        if self.grbl:
            self.grbl.extend_cmd(cmd_list)

    def onCalLaserRunButtonClicked(self):
        if self.wpos['x'] != 0 or self.wpos['y'] != 0:
            info_msg = 'must be at (x,y) = (0,0) to calibrate'
            self.calInfoPlainTextEdit.appendPlainText(info_msg)
            return
        width = self.calPatternWidthDoubleSpinBox.value()
        height = self.calPatternHeightDoubleSpinBox.value()
        feedrate = self.calLaserFeedrateDoubleSpinBox.value()
        power = percent_to_laser_power(self.calLaserPowerDoubleSpinBox.value())
        cmd_list = []
        cmd_list.append(f'G91')
        cmd_list.append(f'F{feedrate:0.1f}')
        cmd_list.append(f'G1 X{-0.5*width:0.3f} Y{-0.5*height:0.3f}')
        cmd_list.append(f'M3 S{power}')
        cmd_list.append(f'G1 X{width:0.3f}')
        cmd_list.append(f'G1 Y{height:0.3f}')
        cmd_list.append(f'G1 X{-width:0.3f}')
        cmd_list.append(f'G1 Y{-height:0.3f}')
        cmd_list.append(f'M5 S0')
        cmd_list.append(f'G1 X{0.5*width:0.3f} Y{0.5*height:0.3f}')
        cmd_list.append(f'G90')
        if self.grbl:
            self.grbl.extend_cmd(cmd_list)
            info_msg = 'running calibration cut'
        else:
            info_msg = 'unable to run, grbl not connected'
        self.calInfoPlainTextEdit.appendPlainText(info_msg)
        self.disable_widgets_on_run()

    def onCalAcceptDataPointsButtonClicked(self):
        if len(self.point_list) >= self.CALIBRATION_MINIMUM_POINTS:
            cal_data = {
                    'image_points'     : self.point_list,
                    'target_width_mm'  : self.calPatternWidthDoubleSpinBox.value(),
                    'target_height_mm' : self.calPatternHeightDoubleSpinBox.value(),
                    }
            self.calibration.update(cal_data)
            self.calInfoPlainTextEdit.appendPlainText('calibration points accepted')
        else:
            self.calInfoPlainTextEdit.appendPlainText('too few calibration points')


    def onCalSaveDataPointsButtonClicked(self):
        self.calibration.save(self.calibration_file_fullpath)
        self.calInfoPlainTextEdit.appendPlainText('calibration points saved')

    def onCalClearDataPointsButtonClicked(self):
        self.point_list = []

    def onCutRunButtonClicked(self):
        if len(self.point_list) <= 1:
            info_msg = 'unable to run, require > 1 point'
            self.cutInfoPlainTextEdit.appendPlainText(info_msg)
            return

        if self.wpos['x'] != 0 or self.wpos['y'] != 0:
            info_msg = 'must be at (x,y) = (0,0) to run cut'
            self.cutInfoPlainTextEdit.appendPlainText(info_msg)
            return

        feedrate = self.cutLaserFeedrateDoubleSpinBox.value()
        power = percent_to_laser_power(self.cutLaserPowerDoubleSpinBox.value())
        point_list_mm = self.calibration.convert_px_to_mm(self.point_list)
        x0, y0 = point_list_mm[0]
        cmd_list = []
        cmd_list.append(f'G90')
        cmd_list.append(f'F{feedrate:0.1f}')
        cmd_list.append(f'G1 X{x0:0.3f} Y{y0:0.3f}')
        cmd_list.append(f'M3 S{power}')
        for x,y in point_list_mm[1:]:
            cmd_list.append(f'G1 X{x:0.3f} Y{y:0.3f}')
        cmd_list.append(f'M5 S0')
        cmd_list.append('G1 X0 Y0')
        if self.grbl:
            self.grbl.extend_cmd(cmd_list)
            info_msg = f'running cut with {len(self.point_list)} points'
        else:
            info_msg = 'unable to run, grbl not connected'
        self.cutInfoPlainTextEdit.appendPlainText(info_msg)

    def onCutClearButtonClicked(self):
        self.point_list = []

    def onImageLeftMouseClick(self, x, y):
        self.point_list.append((x,y))
        self.calibration.convert_px_to_mm(self.point_list)
        if not self.camera_running:
            self.update_image()

    def onImageRightMouseClick(self, x, y):
        self.point_list.pop()
        if not self.camera_running:
            self.update_image()

    def onImageMiddleMouseClick(self, x, y):
        if len(self.point_list) > 2:
            self.point_list.append(self.point_list[0])
        if not self.camera_running:
            self.update_image()
        
    def onClearButtonClicked(self):
        self.point_list = []
        self.update_image()


    def disable_widgets_on_run(self):
        for w in self.widgets_to_disable_on_run:
            w.setEnabled(False)

    def reenable_widgets(self):
        for w in self.widgets_to_disable_on_run:
            w.setEnabled(True)


# -------------------------------------------------------------------------------------------------

def get_usbserial_devices(): 
    port_list = [item.device for item in serial.tools.list_ports.comports()]
    port_list = [item for item in port_list if ('USB' in item) or ('ACM' in item)]
    return port_list

def convert_sec_to_msec(value):
    return 1000.0*value

def app_main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = AppMainWindow()
    mainWindow.showMaximized()
    app.exec_()

def rm_negative_zero(val):
    return abs(val) if val==0 else val

def percent_to_laser_power(percent):
    return int(1000*percent/100.0)


# -------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    app_main()
