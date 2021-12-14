import os
import time
import pickle
import collections
import numpy as np

class ImageStackCollector:

    DEFAULT_IMAGES_PER_STEP = 20 
    DEFAULT_SETTLING_TIME = 2.0

    def __init__(self, min_val=-0.05, max_val=0.05, num=10):
        self.images_per_step = self.DEFAULT_IMAGES_PER_STEP
        self.settling_time = self.DEFAULT_SETTLING_TIME
        self.set_range(min_val, max_val, num)
        self.step_to_image_list = collections.OrderedDict() 
        self.step_to_image_median = collections.OrderedDict()
        self.t_step = 0.0
        self.index = self.num

    def set_range(self, min_val, max_val, num):
        self.steps = np.linspace(min_val, max_val, num)

    @property
    def min_val(self):
        return self.steps.min()

    @property
    def max_val(self):
        return self.steps.max()

    @property
    def num(self):
        return self.steps.size

    @property
    def running(self):
        return self.index < self.num

    @property
    def is_first(self):
        return self.index == -1

    @property
    def step_complete(self):
        if self.running and self.index >= 0:
            val = self.steps[self.index] 
            return len(self.step_to_image_list[val]) >= self.images_per_step
        else:
            return True

    @property
    def settled(self):
        return (time.time() - self.t_step) > self.settling_time

    def start(self):
        self.clear()
        self.index = -1 

    def stop(self):
        self.index = self.num

    def clear(self):
        self.step_to_image_list = collections.OrderedDict() 
        self.step_to_image_median = collections.OrderedDict() 

    def next_step(self):
        if self.index > -1:
            val = self.steps[self.index] 
            image_array = np.array(self.step_to_image_list[val])
            image_median = np.median(image_array, axis=0).astype(np.uint8)
            self.step_to_image_median[val] = image_median
        self.index += 1
        self.t_step = time.time()
        if self.index < self.num:
            val = self.steps[self.index] 
            self.step_to_image_list[val] = [] 
            return val 
        else:
            return None

    def add_image(self, image):
        val = self.steps[self.index] 
        self.step_to_image_list[val].append(image) 

    def save(self, filename='focus_stack.pkl'):
        filepath = os.path.join(os.environ['HOME'], filename)
        data = {
                'raw_images'    : self.step_to_image_list, 
                'median_images' : self.step_to_image_median,
                }
        with open(filepath,'wb') as f:
            pickle.dump(data,f)










