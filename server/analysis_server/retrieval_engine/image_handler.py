### url
import urllib
import requests
### image
import cv2
import imutils
from imutils.object_detection import non_max_suppression as NMS
### text
import pytesseract
import re
### own
from exceptions import *
### 
import sys
import os
import random
import copy
import math
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class ImageHandler(object):
    '''
    -description:
    -input:
    -output:
    '''
    def __init__(self, img=None, img_path=None, path_type=None):
        self.path_type = path_type
        self.img_path = img_path
        if (img_path is None)^(path_type is None):
            raise ImageError('You have to input both img_path and path_type')
        if img is None:
            if img_path is None:
                raise ImageError("You do not input any args. You have to input at least one arg. 'img' or 'img_path'")
            else:
                self.image = self.get_image()
        else:
            self.image = img

    def get_image(self):
        if self.path_type=='url':
            ret = self.get_image_from_url(self.img_path)
        elif self.path_type=='local':
            ret = self.get_image_from_local(self.img_path)
        else:
            raise ImageError("Is it proper img_path?")
        return ret

    def get_image_from_url(self, img_path):
        img_from_url = requests.get(img_path)
        img = np.asarray(bytearray(img_from_url.content), dtype="uint8")
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        return img

    def get_image_from_local(self, img_path):
        return cv2.imread(img_path)

    def save_image(self, save_path):
        '''
        -argument:
            -img:
                -type: opencv image
            -save_path: real path of directory you want to save the image
        '''
        cv2.imwrite(save_path, self.image)
    
    def copy(self, img=None):
        if img is None:
            img = self.image
        return ImageHandler(img=img.copy())

    def augmentate(self, img=None, background=None, background_option=0, rotation_degree=None, flip_option=None, size_constraint=False):
        if img is None:
            img = self.image
        cols, rows, *channels = img.shape
        ret = copy.deepcopy(img)
        if rotation_degree is not None:
            if len(channels)==0:
                plus_one = np.ones((cols, rows), np.uint8)
            else:
                plus_one = np.ones((cols, rows, channels[0]), np.uint8)
            ret = self.im_plus(origin=ret, other=plus_one)
            ret = self.im_rotate(img=ret, degree=rotation_degree)
        if flip_option is not None:
            ret = self.im_flip(img=ret, option=flip_option)
        if background is not None:
            ret = self.im_background(background=background, img=ret, option=background_option)
        if size_constraint:
            ret = self.im_resize(img=ret, x=rows, y=cols)
        return ret

    def find_rectangle(self, img=None):
        if img is None:
            img = self.image
        args = {}
        args["size"] = {}
        args["size"]["width"] = 480
        args["size"]["height"] = 720
        args["median"] = {}
        args["median"]["KSize"] = 5
        args["gauss"] = {}
        args["gauss"]["KRate"] = 0.1
        args["gauss"]["sigmaXH"] = 0
        args["gauss"]["sigmaYH"] = 0
        args["gauss"]["sigmaXW"] = 0
        args["gauss"]["sigmaYW"] = 0
        args["unsharp"] = {}
        args["unsharp"]["KSize"] = (11,15)
        args["unsharp"]["alpha"] = 1
        args["unsharp"]["sigmaX"] = 0
        args["unsharp"]["sigmaY"] = 0
        args["adaBin"] = {}
        args["adaBin"]["method"] = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        args["adaBin"]["type"] = cv2.THRESH_BINARY_INV
        args["adaBin"]["BSize"] = 31
        args["adaBin"]["C"] = 5
        args["morphology"] = {}
        args["morphology"]["KSize"] = (3,4)
        args["morphology"]["shape"] = cv2.MORPH_RECT
        args["morphology"]["it_opening"] = 2
        args["morphology"]["it_closing"] = 8
        args["contour"] = {}
        args["contour"]["mode"] = cv2.RETR_EXTERNAL
        args["contour"]["method"] = cv2.CHAIN_APPROX_NONE

        args["size"]["height_origin"], args["size"]["width_origin"] = img.shape[:2]
        args["size"]["height_rate"] = args["size"]["height_origin"]/args["size"]["height"]
        args["size"]["width_rate"] = args["size"]["width_origin"]/args["size"]["width"]
        resized = self.im_resize(img=img, x=args["size"]["width"], y=args["size"]["height"])

        median = cv2.medianBlur(resized, ksize=args["median"]["KSize"])

        ga_args = args["gauss"]
        gauss_width = round(args["size"]["width"]*ga_args["KRate"])
        gauss_height = round(args["size"]["height"]*ga_args["KRate"])
        if gauss_width%2==0: gauss_width-=1
        if gauss_height%2==0: gauss_height-=1

        gaussed_h = cv2.GaussianBlur(median, ksize=(1,gauss_height), sigmaX=ga_args["sigmaXH"])
        gaussed_w = cv2.GaussianBlur(gaussed_h, ksize=(gauss_width,1), sigmaX=ga_args["sigmaXW"])

        un_args = args["unsharp"]
        gaussed = cv2.GaussianBlur(median, ksize=un_args["KSize"], sigmaX=0)
        unsharp = ImageHandler(img=(1+un_args["alpha"])*gaussed_w.astype(np.int16))
        unsharp = unsharp.im_minus(un_args["alpha"]*gaussed.astype(np.int16))

        gray = ImageHandler(unsharp).im_change_type()

        bin_args = args["adaBin"]
        binary = cv2.adaptiveThreshold(src=gray, maxValue=1, 
                                    adaptiveMethod=bin_args["method"], 
                                    thresholdType=bin_args["type"], 
                                    blockSize=bin_args["BSize"], C=bin_args["C"])

        mor_args = args["morphology"]
        kernel=cv2.getStructuringElement(shape=mor_args["shape"], ksize=mor_args["KSize"])
        morphology = cv2.erode(src=binary, kernel=kernel, iterations=mor_args["it_opening"])
        morphology = cv2.dilate(src=morphology, kernel=kernel, iterations=mor_args["it_opening"]+mor_args["it_closing"])
        morphology = cv2.erode(src=morphology, kernel=kernel, iterations=mor_args["it_closing"])

        cont_args = args["contour"]
        contours, hierarchy = cv2.findContours(morphology, mode=cont_args["mode"], method=cont_args["method"])

        len_contours = [contour.shape[0] for contour in contours]
        main_contour = len_contours.index(max(len_contours))
        contour = contours[main_contour][:,0]

        ret=cv2.boundingRect(contour)
        return ret

    def im_change_type(self, img=None, img_type=cv2.COLOR_BGR2GRAY):
        if img is None:
            img = self.image
        ret = cv2.cvtColor(img, img_type)
        return ret

    def im_minus(self, other, origin=None):
        if origin is None:
            origin = self.image
        ret = origin.astype(np.int16) - other.astype(np.int16)
        is_underflow = ret < 0
        ret *= is_underflow ^ True
        return ret.astype(np.uint8)

    def im_plus(self, other, origin=None):
        if origin is None:
            origin = self.image
        ret = origin.astype(np.int16) + other.astype(np.int16)
        is_overflow = (ret > 255)
        ret *= is_overflow ^ True
        ret += is_overflow * 255
        return ret.astype(np.uint8)

    def im_resize(self, img=None, x=None, y=None, option=cv2.INTER_LINEAR):
        if img is None:
            img = self.image
        if x is None:
            y = img.shape[0]
        if y is None:
            x = img.shape[1]
        ret = cv2.resize(img, dsize=(x,y), interpolation=option)
        return ret

    def im_get_area(self, points, img=None, ratio=2.):
        if img is None:
            img = self.image
        start_x, end_x, start_y, end_y = points
        len_x = end_x - start_x
        len_y = end_y - start_y
        new_len_x = ratio * len_x
        new_len_y = ratio * len_y
        diff_x = (new_len_x - len_x)/2
        diff_y = (new_len_y - len_y)/2
        start_x -= diff_x
        end_x += diff_x
        start_y -= diff_y
        end_y += diff_y
        if start_x >= end_x or start_y >= end_y:
            raise ValueError("new area is not proper")
        if start_x <0: start_x = 0
        if start_y <0: start_y = 0
        if end_x > img.shape[1]: end_x= img.shape[1]
        if end_y > img.shape[0]: end_y= img.shape[0]
        return (int(start_x), int(end_x), int(start_y), int(end_y))

    def im_padding(self, big_size_img, small_size_img=None, value=0, padding=None, borderType=cv2.BORDER_CONSTANT, option=0):
        '''
        - option
            - 0: middle of big_size_img
            - 1: uniform random position
            - 2: 지정한만큼 패딩
        '''
        if small_size_img is None:
            small_size_img = self.image
        adding_height = big_size_img.shape[0] - small_size_img.shape[0]
        adding_width = big_size_img.shape[1] - small_size_img.shape[1]
        if adding_height <2 or adding_width <2:
            raise ValueError("too small big_size_img")
        if option == 0:
            height_rest = width_rest = 0
            if adding_height%2==1: 
                height_rest = 1
            if adding_width%2==1: 
                width_rest = 1
            top = int(adding_height/2)
            bottom = top+height_rest
            left = int(adding_width/2)
            right = left+width_rest
        elif option == 1:
            top = random.randint(1, adding_height)
            bottom = adding_height-top
            left = random.randint(1, adding_width)
            right = adding_width-left
        elif option == 2:
            if padding is None:
                top = bottom = left = right = 0
            else:
                top, bottom, left, right = padding
        else:
            raise ValueError("undefiend option")
        ret = cv2.copyMakeBorder(small_size_img, top, bottom, left, right, borderType=borderType, value=value)
        return ret

    def im_rotate(self, img=None, degree=90):
        '''
        - description: rotate counterclockwise without cropping
        '''
        if img is None:
            img = self.image
        cols, rows, *channels = img.shape
        new_row = math.ceil(np.sqrt(rows**2+cols**2))
        if len(channels) == 0:
            background = np.zeros((new_row, new_row), np.uint8)
        else:
            background = np.zeros((new_row, new_row, channels[0]), np.uint8)
        padded_img = self.im_padding(background, img)
        rotated_img = imutils.rotate(padded_img, degree)
        return rotated_img

    def im_crop(self, img=None):
        if img is None:
            img = self.image

    def im_flip(self, img=None, option=0):
        '''
        - option
            - 0: filp over x-axis
            - 1: filp over y-axis
            - -1: filp over Origin(원점)
        '''
        if img is None:
            img = self.image
        return cv2.flip(img, option)

    def im_translate(self, img=None, x=0, y=0):
        if img is None:
            img = self.image
        return imutils.translate(img, x, y)

    def im_shear(self, img=None):
        if img is None:
            img = self.image

    def im_background(self, background, img=None, padding=None, option=0):
        if img is None:
            img = self.image
        cols, rows, *channels = img.shape
        padded_img = self.im_padding(background, img, padding=padding, option=option)
        is_it_background = padded_img==0
        background_hole = background*is_it_background
        ret = self.im_plus(background_hole, padded_img)
        return ret

    def im_perspective(self, origin_points, img=None, new_width=None, new_height=None, interpolation=cv2.INTER_LINEAR):
        if img is None:
            img = self.image
        if new_width is None:
            new_width = img.shape[1]
        if new_height is None:
            new_height = img.shape[0]
        new_points = [[0,0], [new_width, 0], [new_height, 0], [new_width, new_height]]
        M = cv2.getPerspectiveTransform(np.float32(origin_points), np.float32(new_points))
        ret = cv2.wrapPerspective(img, M, dsize=(new_width, new_height), flags=interpolation)
        return ret