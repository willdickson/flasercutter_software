import collections
import numpy as np

class ImageStackCollector:

    DEFAULT_SLEEP_DT = 0.1
    DEFAULT_IMAGES_PER_STEP = 10 

    def __init__(self, min_val=-0.05, max_val=0.05, num=10):
        self.sleep_dt = self.DEFAULT_SLEEP_DT
        self.images_per_step = self.DEFAULT_IMAGES_PER_STEP
        self.set_range(min_val, max_val, num)
        self.images = collections.OrderedDict() 

    def set_range(self, min_val, max_val, num):
        self.steps = np.linspace(min_val, max_val, num)
        self.index = self.num

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
        if self.running:
            val = self.steps[self.index] 
            return len(self.images[val]) >= self.images_per_step
        else:
            return True

    def start(self):
        self.clear()
        self.index = -1 

    def stop(self):
        self.index = self.num

    def clear(self):
        self.images = collections.OrderedDict() 

    def next_step(self):
        self.index += 1
        if self.index < self.num:
            val = self.steps[self.index] 
            self.images[val] = [] 
            return val 
        else:
            return None

    def add_image(self, image):
        val = self.steps[self.index] 
        self.images[val].append(image) 










