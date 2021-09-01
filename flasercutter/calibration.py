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

    @property
    def mm_to_pix(self):
        if self.vals:
            rval = self.vals['x_mm_per_px'], self.vals['y_mm_per_px']
        else:
            rval = None
            
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
        x_mm_per_px = self.data['target_width_mm']/float(dx_px)
        y_mm_per_px = self.data['target_height_mm']/float(dy_px)
        self.vals['x_mm_per_px'] = x_mm_per_px
        self.vals['y_mm_per_px'] = y_mm_per_px
        self.vals['cx_laser_px'] = cx_px
        self.vals['cy_laser_px'] = cy_px

        # New method
        # -------------------------------------------------

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
        homography, mask = cv2.findHomography(np.array(point_list_px), np.array(point_list_mm), 0)
        print(homography)


    def convert_px_to_mm(self, points_px):
        cx = self.vals['cx_laser_px']
        cy = self.vals['cy_laser_px']
        sx = self.vals['x_mm_per_px']
        sy = self.vals['y_mm_per_px']
        points_mm = [(sx*(x-cx), -sy*(y-cy)) for x,y in points_px]
        return points_mm

    def convert_mm_to_px(self, points_mm):
        cx = self.vals['cx_laser_px']
        cy = self.vals['cy_laser_px']
        sx = 1.0/self.vals['x_mm_per_px']
        sy = 1.0/self.vals['y_mm_per_px']
        points_px = [(x*sx+cx, y*sy+cy) for x,y in points_mm]
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




