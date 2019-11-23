import cv2
import math
import os

IE = 1.767145
UMPX = 3.7

def plotGray(img):
  im = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
  plt.imshow(im)

def calcIslets(img, low=230, high=255):
  mask = cv2.inRange(img, low, high)
  _, contours, _  = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  areas = [contourArea(cont) for cont in contours] 
  volumes = [calcEllipseArea(cont) for cont in contours] 
  return (len(contours), areas, volumes)


def calcEllipseArea(cont, ie = IE, umpx=UMPX):
  ellipse = cv2.fitEllipse(cont)
  _, (w, h), _ = ellipse
  a = (w*umpx)/2
  b = (h*umpx)/2
  area = math.pi * a * b
  return area * ie

def contourArea(cont, ie = IE, umpx=UMPX):
  area = cv2.contourArea(cont)
  return area * umpx * ie 

def calcEllipseVolume(cont, ie = IE, umpx=UMPX):
  ellipse = cv2.fitEllipse(cont)
  _, (w_px, h_px), _ = ellipse
  w_um = w_px * umpx
  h_um = h_px * umpx
  a = (w_um)/2
  b = (h_um)/2
  vol = 4/3*math.pi * a/2 * (b/2)**2
  return vol * ie


def batchCalc(imgs, name="--"):
  cnts = []
  areass = [] 
  volumess = []
  purs = []

  print("cnt", "\t", "purity")

  for img in imgs:
    #img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    cnt, areas, volumes = calcIslets(img)
    vol_sum = sum(volumes)
    pur = calcPurity(img)

    cnts.append(cnt)
    areass.append(areas)
    volumess.append(volumes)
    purs.append(pur)
    print(cnt, "\t", round(pur, 2), "\t", os.path.basename(name))

  return (cnts, purs)

def calcPurity(img):
  mask_islets = cv2.inRange(img, 255, 255)
  mask_exo = cv2.inRange(img, 20, 230)
   _, contours_islets, _  = cv2.findContours(mask_islets, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  _, contours_exo, _  = cv2.findContours(mask_exo, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  islets_area = sum([contourArea(cont) for cont in contours_islets])
  exo_area = sum([contourArea(cont) for cont in contours_exo])

  return islets_area / (islets_area +  exo_area)


