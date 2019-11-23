import cv2
import math
import os

IE = 1.767145
UMPX = 3.7

def plotGray(img):
  im = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
  plt.imshow(im)

def findContours(img):
  if (cv2.__version__ == '4.1.1'):
    contours, hier = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours
  else:
    _, contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours
    

def calcIslets(img, low=230, high=255):
  mask = cv2.inRange(img, low, high)
  contours = findContours(mask)
  areas = [contourArea(cont) for cont in contours] 
  volumes = [calcEllipseArea(cont) for cont in contours] 
  return (len(contours), areas, volumes)


def calcEllipseArea(cont, ie = IE, umpx=UMPX):
  try:
    ellipse = cv2.fitEllipse(cont)
    _, (w, h), _ = ellipse
    a = (w*umpx)/2
    b = (h*umpx)/2
    area = math.pi * a * b
    return area * ie
  except Exception as e:
    return 0

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


def batchCalc(imgs, names):
  cnts = []
  areass = [] 
  volumess = []
  purs = []

  print("cnt", "\t", "purity")

  for i, img in enumerate(imgs):
    try:
        #img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        cnt, areas, volumes = calcIslets(img)
        vol_sum = sum(volumes)
        pur = calcPurity(img)

        cnts.append(cnt)
        areass.append(areas)
        volumess.append(volumes)
        purs.append(pur)
        name = os.path.basename(names[i])
        print(cnt, "\t", round(pur, 2), "\t", name)
    except Exception as e:
        print(names[i])
        print(e)

  return (cnts, purs)

def calcPurity(img):
  mask_islets = cv2.inRange(img, 255, 255)
  mask_exo = cv2.inRange(img, 1, 254)
  contours_islets = findContours(mask_islets)
  contours_exo = findContours(mask_exo)
  islets_area = sum([contourArea(cont) for cont in contours_islets])
  exo_area = sum([contourArea(cont) for cont in contours_exo])

  return islets_area / (islets_area +  exo_area)


def pil2cv(pil_img):
  return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
