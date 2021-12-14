# -*- coding: utf-8 -*-
"""
This code and algorithm was inspired and adapted from the following sources:
http://stackoverflow.com/questions/15911783/what-are-some-common-focus-stacking-algorithms
https://github.com/cmcguinness/focusstack
https://github.com/momonala/focus-stack

"""

import logging
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.WARNING)


class FocusStacker(object):

    def __init__(self, laplacian_kernel_size: int = 5, gaussian_blur_kernel_size: int = 5) -> None:
        """Focus stacking class.
        Args:
            laplacian_kernel_size:      Size of the laplacian window. Must be odd.
            gaussian_blur_kernel_size:  How big of a kernel to use for the gaussian blur. 
                                        Must be odd.
        """
        self._laplacian_kernel_size = laplacian_kernel_size
        self._gaussian_blur_kernel_size = gaussian_blur_kernel_size

    def focus_stack(self, images: List[np.ndarray], depths: List[float]) -> np.ndarray:
        """Pipeline to focus stack a list of images."""
        laplacian = self.compute_laplacian(images)
        focus_stacked = self.find_focus_regions(images, depths, laplacian)
        return focus_stacked


    def compute_laplacian(self, images: List[np.ndarray],) -> np.ndarray:
        """Gaussian blur and compute the gradient map of the image. This is
        proxy for finding the focus regions.

        Args:
            images: image data
        """
        logger.info("Computing the laplacian of the blurred images")
        laplacians = []
        for image in images:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(
                gray,
                (self._gaussian_blur_kernel_size, self._gaussian_blur_kernel_size),
                0,
            )
            laplacian_gradient = cv2.Laplacian(
                blurred, cv2.CV_64F, ksize=self._laplacian_kernel_size
            )
            laplacians.append(laplacian_gradient)
        laplacians = np.asarray(laplacians)
        logger.debug(f"Shape of array of laplacian gradient: {laplacians.shape}")
        return laplacians

    def find_focus_regions(self, images: List[np.ndarray], depths: List[float], 
            laplacian_gradient: np.ndarray) -> np.ndarray:
        """Take the absolute value of the Laplacian (2nd order gradient) of the
        Gaussian blur result.  This will quantify the strength of the edges
        with respect to the size and strength of the kernel (focus regions).

        Then create a blank image, loop through each pixel and find the
        strongest edge in the LoG (i.e. the highest value in the image stack)
        and take the RGB value for that pixel from the corresponding image.

        Then for each pixel [x,y] in the output image, copy the pixel [x,y]
        from the input image which has the largest gradient [x,y]

        Args:
            images:              list of image data to focus and stack.
            depths:              list of depth data from focus stack acquisition
            laplacian_gradient:  the laplacian of the stack. This is the proxy for 
                                 the focus region. Should be size: (len(images), 
                                 images.shape[0], images.shape[1])

        Returns:
            focus_image: np.array of image data of focus stacked image, size of
                         orignal image

            depth_image: np.array of depth data of focus stacked image, size of
                         orignal image

        """
        logger.info("Using laplacian gradient to find regions of focus, and stack.")
        focus_image = np.zeros(shape=images[0].shape, dtype=images[0].dtype)
        depth_image = np.zeros(shape=(images[0].shape[0], images[0].shape[1]), dtype=depths[0].dtype)
        abs_laplacian = np.absolute(laplacian_gradient)
        maxima = abs_laplacian.max(axis=0)
        bool_mask = np.array(abs_laplacian == maxima)
        mask = bool_mask.astype(np.uint8)

        for i, img in enumerate(images):
            focus_image = cv2.bitwise_not(img, focus_image, mask=mask[i])
        focus_image = np.iinfo(focus_image.dtype).max - focus_image

        for i, val in enumerate(depths):
            depth_image[bool_mask[i]] = val

        return focus_image, depth_image
