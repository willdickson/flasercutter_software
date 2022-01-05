import os
import sys
import cv2
import pickle
import sgolay2
import numpy as np
import scipy.ndimage as ndimage
import matplotlib.pyplot as plt
import focus_stacker

def load_data(filename):
    data = None
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data

# -----------------------------------------------------------------------------
if __name__ == '__main__':

    filename = sys.argv[1]
    data = load_data(filename)
    save_medians = False 
    show_images = False

    image_list = []
    depth_list = []

    for i, z in enumerate(data):
        depth_list.append(z)
        if type(data[z]) == list:
            image_array = np.array(data[z])
            image_median = np.median(image_array, axis=0).astype(np.uint8)
            image_list.append(image_median)
        else:
            image_list.append(data[z])
        if show_images:
            print(f'{i+1}/{len(data)}, z={z:0.3f}')
            cv2.imshow('median', image_median)
            if cv2.waitKey(1) & 0xFF == ord('q'):
              break

    if save_medians:
        d = dict(zip(depth_list,image_list))
        basename, ext = os.path.splitext(filename)
        new_filename = f'{basename}_median{ext}'
        with open(new_filename,'wb') as f:
            pickle.dump(d,f)

    fs = focus_stacker.FocusStacker()
    focus_image, depth_image = fs.focus_stack(image_list, depth_list)
    focus_image_gray = cv2.cvtColor(focus_image, cv2.COLOR_BGR2GRAY)

    k = 21 
    depth_image = ndimage.median_filter(depth_image, (k,k))
    print(depth_image.shape)

    #depth_image = depth_image.astype(np.float32)
    #depth_image = cv2.GaussianBlur(depth_image, (11,11), 10)
    #for i in range(1):
    #    depth_image = cv2.medianBlur(depth_image, 5)

    sg2 = sgolay2.SGolayFilter2(window_size=51, poly_order=3)
    depth_image = sg2(depth_image)


    if 0:
        focus_image_yuv = cv2.cvtColor(focus_image, cv2.COLOR_BGR2YUV)
        focus_image_yuv[:,:,0] = cv2.equalizeHist(focus_image_yuv[:,:,0])
        focus_image= cv2.cvtColor(focus_image_yuv, cv2.COLOR_YUV2RGB)
    else:
        focus_image = cv2.cvtColor(focus_image, cv2.COLOR_BGR2RGB)

    fig1, ax1 = plt.subplots(1)
    ax1.imshow(focus_image)
    ax1.axis('off')

    fig2, ax2 = plt.subplots(1)
    ax2.imshow(depth_image,cmap='viridis_r')
    ax2.axis('off')

    x = np.arange(depth_image.shape[1])
    y = np.arange(depth_image.shape[0])
    x,y = np.meshgrid(x,y)

    fig3, ax3 = plt.subplots(1, subplot_kw={'projection':'3d'})
    ax3.plot_surface(x,np.flipud(y),depth_image,cmap='viridis_r')



    plt.show()

    #cv2.imshow('focus', focus_image)
    #cv2.waitKey(0) 












