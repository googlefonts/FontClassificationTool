#!/usr/bin/env python3
import csv
from math import floor
import sys

try: 
  from PIL import (Image, 
                   ImageDraw, 
                   ImageFont) 
except: 
  sys.exit("Needs pillow.\n\npip3 install pillow") 
 

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
  print ("Computing... {}".format(fontfile))

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

  x_height = font.getsize("x")[1]
  width = text_width / float(x_height)

  return darkness, width#, get_base64_image(img)



def find_extremes(d):
  """ Input: a dict key:value
      Output: min and max values from all elements in the dict
  """
  values = d.values()
  return min(values), max(values)


def group_by_attributes(filenames):
  """ Classify a set of fonts by their ammount of black ink (percentage of dark
      pixels in a reference paragraph of text) and attribute a normalized score
      from 1 to 10 based on their computed darkness, effectively grouping the
      fonts by their weight.

      Input: a list of font filenames
      Output: a dict filename:value
              where value is a weight score from 1 (lightest) to 10 (darkest)
  """
  darkness = {}
  width = {}
  for name in filenames:
    darkness[name], width[name] = compute_darkness_and_width(name)

  # normalize weight values:
  min_dark, max_dark = find_extremes(darkness)
  dark_range = max_dark - min_dark

  if dark_range == 0: # unlikely
    weights = {name: 5 for name in filenames}
  else:
    weights = {}
    for name in filenames:
      weights[name] = int(1 + floor(10 * ((darkness[name] - min_dark)/ dark_range)))

  # normalize width values:
  min_width, max_width = find_extremes(width)
  width_range = max_width - min_width

  if width_range == 0: # unlikely
    widths = {name: 5 for name in filenames}
  else:
    widths = {}
    for name in filenames:
      widths[name] = int(1 + floor(10 * ((width[name] - min_width)/ width_range)))

  return weights, widths


def save_csv(filename, metadata):
  with open(filename, 'w') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='"', lineterminator='\n')
    writer.writerow(["GFN","FWE","FIA","FWI","USAGE", "LANGUAGES"]) # first row has the headers
    for gfn in sorted(metadata.keys()):
      data = metadata[gfn]
      fwe = data['weight_int']
      fia = data['angle_int']
      fwi = data['width_int']
      usage = data['usage']
      subsets = data['subsets']
      writer.writerow([gfn, fwe, fia, fwi, usage, subsets])


def read_csv(filename):
  metadata = {}
  with open(filename) as csvfile:
    existing_data = csv.reader(csvfile, delimiter=',', quotechar='"')
    next(existing_data) # skip first row as its not data
    for row in existing_data:
      gfn = row[0]
      if len(row) < 6:
        subsets = None
      else:
        subsets = row[5]

      metadata[gfn] = {
        "weight_int": int(row[1]),
        "angle_int": int(row[2]),
        "width_int": int(row[3]),
        "usage": row[4],
        "subsets": subsets
      }
  return metadata


# Fonts that cause problems: any filenames containing these letters
# will be skipped.
# TODO: Investigate why these don't work.
BLACKLIST = [
#IOError: execution context too long (issue #703)
  "Padauk",
  "KumarOne",
#ZeroDivisionError: float division by zero
  "AdobeBlank",
  "Phetsarath",
# IOError: invalid reference See also: https://github.com/google/fonts/issues/132#issuecomment-244796023
  "Corben",
# IOError: stack overflow on text_width, text_height = font.getsize(TEXT) 
  "Rubik",
]

def is_blacklisted(filename):
  """Returns whether a font is on the blacklist."""

  # first check for explicit blacklisting:
  for name in BLACKLIST:
    if name in filename:
      return True

# Sample code below was copied from
# https://www.cairographics.org/cookbook/freetypepython/
import ctypes as ct
import cairo
class PycairoContext(ct.Structure):
    _fields_ = \
        [
            ("PyObject_HEAD", ct.c_byte * object.__basicsize__),
            ("ctx", ct.c_void_p),
            ("base", ct.c_void_p),
        ]

_initialized = False
def create_cairo_font_face_for_file (filename, faceindex=0, loadoptions=0):
    "given the name of a font file, and optional faceindex to pass to FT_New_Face" \
    " and loadoptions to pass to cairo_ft_font_face_create_for_ft_face, creates" \
    " a cairo.FontFace object that may be used to render text with that font."
    global _initialized
    global _freetype_so
    global _cairo_so
    global _ft_lib
    global _ft_destroy_key
    global _surface

    CAIRO_STATUS_SUCCESS = 0
    FT_Err_Ok = 0

    if not _initialized:
        # find shared objects
        _freetype_so = ct.CDLL("libfreetype.so.6")
        _cairo_so = ct.CDLL("libcairo.so.2")
        _cairo_so.cairo_ft_font_face_create_for_ft_face.restype = ct.c_void_p
        _cairo_so.cairo_ft_font_face_create_for_ft_face.argtypes = [ ct.c_void_p, ct.c_int ]
        _cairo_so.cairo_font_face_get_user_data.restype = ct.c_void_p
        _cairo_so.cairo_font_face_get_user_data.argtypes = (ct.c_void_p, ct.c_void_p)
        _cairo_so.cairo_font_face_set_user_data.argtypes = (ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p)
        _cairo_so.cairo_set_font_face.argtypes = [ ct.c_void_p, ct.c_void_p ]
        _cairo_so.cairo_font_face_status.argtypes = [ ct.c_void_p ]
        _cairo_so.cairo_font_face_destroy.argtypes = (ct.c_void_p,)
        _cairo_so.cairo_status.argtypes = [ ct.c_void_p ]
        # initialize freetype
        _ft_lib = ct.c_void_p()
        status = _freetype_so.FT_Init_FreeType(ct.byref(_ft_lib))
        if  status != FT_Err_Ok :
            raise RuntimeError("Error %d initializing FreeType library." % status)

        _surface = cairo.ImageSurface(cairo.FORMAT_A8, 0, 0)
        _ft_destroy_key = ct.c_int() # dummy address
        _initialized = True

    ft_face = ct.c_void_p()
    cr_face = None
    try :
        # load FreeType face
        status = _freetype_so.FT_New_Face(_ft_lib, filename.encode("utf-8"), faceindex, ct.byref(ft_face))
        if status != FT_Err_Ok :
            raise RuntimeError("Error %d creating FreeType font face for %s" % (status, filename))

        # create Cairo font face for freetype face
        cr_face = _cairo_so.cairo_ft_font_face_create_for_ft_face(ft_face, loadoptions)
        status = _cairo_so.cairo_font_face_status(cr_face)
        if status != CAIRO_STATUS_SUCCESS :
            raise RuntimeError("Error %d creating cairo font face for %s" % (status, filename))

        # Problem: Cairo doesn't know to call FT_Done_Face when its font_face object is
        # destroyed, so we have to do that for it, by attaching a cleanup callback to
        # the font_face. This only needs to be done once for each font face, while
        # cairo_ft_font_face_create_for_ft_face will return the same font_face if called
        # twice with the same FT Face.
        # The following check for whether the cleanup has been attached or not is
        # actually unnecessary in our situation, because each call to FT_New_Face
        # will return a new FT Face, but we include it here to show how to handle the
        # general case.
        if _cairo_so.cairo_font_face_get_user_data(cr_face, ct.byref(_ft_destroy_key)) == None :
            status = _cairo_so.cairo_font_face_set_user_data \
              (
                cr_face,
                ct.byref(_ft_destroy_key),
                ft_face,
                _freetype_so.FT_Done_Face
              )
            if status != CAIRO_STATUS_SUCCESS :
                raise RuntimeError("Error %d doing user_data dance for %s" % (status, filename))

            ft_face = None # Cairo has stolen my reference

        # set Cairo font face into Cairo context
        cairo_ctx = cairo.Context(_surface)
        cairo_t = PycairoContext.from_address(id(cairo_ctx)).ctx
        _cairo_so.cairo_set_font_face(cairo_t, cr_face)
        status = _cairo_so.cairo_font_face_status(cairo_t)
        if status != CAIRO_STATUS_SUCCESS :
            raise RuntimeError("Error %d creating cairo font face for %s" % (status, filename))

    finally :
        _cairo_so.cairo_font_face_destroy(cr_face)
        _freetype_so.FT_Done_Face(ft_face)

    # get back Cairo font face as a Python object
    face = cairo_ctx.get_font_face()
    return face

if __name__ == '__main__':
    face = create_cairo_font_face_for_file("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 128, 128)
    ctx = cairo.Context(surface)

    ctx.set_font_face(face)
    ctx.set_font_size(30)
    ctx.move_to(0, 44)
    ctx.show_text("Hello,")
    ctx.move_to(30, 74)
    ctx.show_text("world!")

    del ctx

    surface.write_to_png("hello.png")
#end if

