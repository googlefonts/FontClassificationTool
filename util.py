#!/usr/bin/env python3
import csv

try: 
  from PIL import (Image, 
                   ImageDraw, 
                   ImageFont) 
except: 
  sys.exit("Needs pillow.\n\npip install pillow") 
 

# The text used to test weight and width. Note that this could be
# problematic if a given font doesn't have latin support.
TEXT = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvXxYyZz"

# This text-block results in a better calculation of "darkness":
TEXT_MULTILINE = ("AaBbCcDdEeAaBbCcDdEe\n"
                  "FfGgHhIiJjFfGgHhIiJj\n"
                  "KkLlMmNnOoKkLlMmNnOo\n"
                  "PpQqRrSsTtPpQqRrSsTt\n"
                  "UuVvXxYyZzUuVvXxYyZz")
FONT_SIZE=30


def compute_darkness_and_width(fontfile):
  """Returns the darkness and width of a given a TTF.

     Darkness value is a percentage
     Width is in pixels

     Both values should be normalized.
  """

  # Render the test text using the font onto an image.
  font = ImageFont.truetype(fontfile, FONT_SIZE)
  text_width, text_height = font.getsize(TEXT_MULTILINE)

  # This is a trick to get a full block of text avoiding the
  # beggining and end and sides of the actual rendered string
  # bounding-box, because PIL seems to be bugged and sometimes
  # adds some spurious white-space which would introduce
  # errors in our calculation of the font darkness value:
  img = Image.new('RGBA', (int(text_width/10), int(5*text_height)))
  draw = ImageDraw.Draw(img)
  draw.text((-text_width/20, int(-2.5*text_height)),
            TEXT_MULTILINE + '\n' + TEXT_MULTILINE,
            font=font, fill=(0, 0, 0))

  # Calculate the average darkness.
  histogram = img.histogram()
  avg = 0.0
  for i in range(256):
    alpha = histogram[i + 3*256]
    avg += (i / 255.0) * alpha

  darkness = avg / (text_width * text_height)
  return darkness, text_width#, get_base64_image(img)



def find_extremes(d):
  """ Input: a dict key:value
      Output: min and max values from all elements in the dict
  """
  values = d.values()
  return min(values), max(values)


def group_by_weight(filenames):
  """ Classify a set of fonts by their ammount of black ink (percentage of dark
      pixels in a reference paragraph of text) and attribute a normalized score
      from 1 to 10 based on their computed darkness, effectively grouping the
      fonts by their weight.

      Input: a list of font filenames
      Output: a dict filename:value
              where value is a weight score from 1 (lightest) to 10 (darkest)
  """
  darkness = {name: compute_darkness_and_width(name)[0] for name in filenames}
  min_dark, max_dark = find_extremes(darkness)
  dark_range = max_dark - min_dark

  # unlikely:
  if dark_range == 0:
    return {name: 5 for name in filenames}

  weights = {}
  for name in filenames:
    weights[name] = int(1 + 9 * ((darkness[name] - min_dark)/ dark_range))

  return weights


def save_csv(filename, metadata):
  with open(filename, 'w') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='"', lineterminator='\n')
    writer.writerow(["GFN","FWE","FIA","FWI","USAGE"]) # first row has the headers
    for gfn in sorted(metadata.keys()):
      data = metadata[gfn]
      fwe = data['weight_int']
      fia = data['angle_int']
      fwi = data['width_int']
      usage = data['usage']
      writer.writerow([gfn, fwe, fia, fwi, usage])
