import io
import os
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math

basepath = "segs/"

img_paths = [basepath + name for name in os.listdir(basepath)]


imgs = [cv2.imread(img_path, cv2.IMREAD_GRAYSCALE) for img_path in img_paths]

from calcs import batchCalc, pil2cv

res = batchCalc(imgs, img_paths)
