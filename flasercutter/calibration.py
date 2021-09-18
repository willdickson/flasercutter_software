import os
import pickle
import cv2
import numpy as np

class Calibration:

    def __init__(self):
        self.data = {}
        self.vals = {}

    @property
    def ok(self):
        if self.data:
            rval = True
        else:
            rval = False
        return rval

    @property
    def laser_pos_px(self):
        if self.vals:
            rval = self.vals['cx_laser_px'], self.vals['cy_laser_px']
        else:
            rval = None
        return rval

    def update(self,data):
        self.data = data
        self.calc_vals_from_data()

    def calc_vals_from_data(self):
        x_list = [x for x,y in self.data['image_points']]
        y_list = [y for x,y in self.data['image_points']]
        dx_px = max(x_list) - min(x_list)
        dy_px = max(y_list) - min(y_list)
        cx_px = 0.5*(max(x_list) + min(x_list))
        cy_px = 0.5*(max(y_list) + min(y_list))
        self.vals['cx_laser_px'] = cx_px
        self.vals['cy_laser_px'] = cy_px

        # Get point correspondences 
        w = self.data['target_width_mm']
        h = self.data['target_height_mm']
        point_list_mm = [(-w/2,-h/2), (w/2,-h/2), (w/2,h/2), (-w/2,h/2)]
        
        # Sort image points into the same order
        image_points = [(x-cx_px, y-cy_px) for x, y in self.data['image_points']]
        image_points.sort(key=lambda x: x[0])
        image_points_lhs = image_points[:2]
        image_points_rhs = image_points[2:]
        image_points_lhs.sort(key=lambda x: x[1])
        image_points_rhs.sort(key=lambda x: x[1])
        point_list_px = [
                image_points_lhs[1],
                image_points_rhs[1], 
                image_points_rhs[0], 
                image_points_lhs[0]
                ]
        array_px = np.array(point_list_px)
        array_mm = np.array(point_list_mm)
        homography, mask = cv2.findHomography(array_px, array_mm, 0)
        self.vals['homography'] = homography
        self.vals['homography_inv'] = np.linalg.inv(homography)

        print(f'data: {self.data}')
        print(f'vals: {self.vals}')

    def convert_px_to_mm(self, points_px):
        cx = self.vals['cx_laser_px']
        cy = self.vals['cy_laser_px']
        homography = self.vals['homography']
        array_px = np.array(points_px,dtype=np.float) - np.array([cx,cy])
        array_mm = cv2.perspectiveTransform(array_px.reshape(-1,1,2),homography)
        array_mm = array_mm.reshape(-1,2)
        points_mm = array_mm.tolist() 
        return points_mm

    def convert_mm_to_px(self, points_mm):
        cx = self.vals['cx_laser_px']
        cy = self.vals['cy_laser_px']
        homography_inv = self.vals['homography_inv']
        array_mm = np.array(points_mm,dtype=np.float)
        array_px = cv2.perspectiveTransform(array_mm.reshape(-1,1,2),homography)
        array_px = array_px.reshape(-1,2) + np.array([cx,cy])
        points_px = array_px.tolist()
        return points_px

    def load(self, filename):
        try:
            with open(filename,'rb') as f: 
                data = pickle.load(f) 
            self.update(data)
            rval = True
            msg = ''
        except Exception as err:
            rval = False
            msg = str(err)
        return rval, msg 

    def save(self, filename):
        try:
            with open(filename,'wb') as f:
                pickle.dump(self.data,f)
            rval = True
            msg = ''
        except Exception as err:
            rval = False
            msg = str(err)
        return rval, msg




