#!/usr/bin/env python2
# coding: utf-8
# Copyright 2013 The Font Bakery Authors. All Rights Reserved.
# Copyright 2017 The Google Font Tools Authors
# Copyright 2018 The Font Classification Tool Authors:
#                - Felipe C. da S. Sanches
#                - Dave Crossland
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Initially authored by Google and contributed by Filip Zembowicz.
# Further improved by Dave Crossland and Felipe Sanches.
#
# OVERVIEW + USAGE
#
# font-classification-tool.py -h
#
import argparse
import collections
import csv
import glob
import math
import os
import StringIO
import sys
import re
import errno
from fonts_public_pb2 import FamilyProto
from constants import (NAMEID_FONT_FAMILY_NAME,
                       NAMEID_FONT_SUBFAMILY_NAME)
from gfn import GFN_from_filename

import cairo
from util import create_cairo_font_face_for_file, PycairoContext


DESCRIPTION = """Calculates the visual weight, width or italic angle of fonts.

  For width, it just measures the width of how a particular piece of text renders.

  For weight, it measures the darkness of a piece of text.

  For italic angle it defaults to the italicAngle property of the font.

  Then it starts a HTTP server and shows you the results, or
  if you pass --debug then it just prints the values.

  Example (all Google Fonts files, all existing data):
    font-classification-tool.py --files="fonts/*/*/*.ttf" --existing=fonts/tools/font-metadata.csv
"""

parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-f", "--files", default="*", required=True, nargs="+",
                    help="The pattern to match for finding ttfs, eg 'folder_with_fonts/*.ttf'.")
parser.add_argument("-d", "--debug", default=False, action='store_true',
                    help="Debug mode, just print results")
parser.add_argument("-e", "--existing", default=False,
                    help="Path to existing font-metadata.csv")
parser.add_argument("-m", "--missingmetadata", default=False, action='store_true',
                    help="Only process fonts for which metadata is not available yet")
parser.add_argument("-o", "--output", default="output.csv", required=True,
                    help="CSV data output filename")

#TODO: make these available as CLI arguments as well:
VERBOSE=True


try:
  from flask import (Flask,
                     jsonify,
                     request,
                     send_from_directory)

except:
  sys.exit("Needs flask.\n\npip install flask")


# At some point we may want to regenerate these images using cairo code
# but for now I think it is enough to simply usethe generated PNGs commited to the git repo.
#
#def generate_italic_angle_images():
#  for i in range(10):
#    angle = 30*(float(i)/10) * 3.1415/180
#    width = 2000
#    height = 500
#    lines = 250
#    im = Image.new('RGBA', (width,height), (255,255,255,0))
#    spacing = width/lines
#    draw = ImageDraw.Draw(im)
#    for j in range(lines):
#      draw.line([j*spacing - 400, im.size[1], j*spacing - 400 + im.size[1]*math.tan(angle), 0], fill=(50,50,255,255))
#    del draw
#
#    imagesdir = os.path.join(os.path.dirname(__file__), "font_classification_tool", "images")
#    if not os.path.isdir(imagesdir):
#       os.mkdir(imagesdir)
#    filepath = os.path.join(imagesdir, "angle_{}.png".format(i+1))
#    im.save(filepath, "PNG")


def normalize_values(properties, target_max=1.0):
  """Normalizes a set of values from 0 to target_max"""
  max_value = 0.0
  for i in range(len(properties)):
    val = float(properties[i]['value'])
    max_value = max(max_value, val)
  for i in range(len(properties)):
    properties[i]['value'] *= (target_max/max_value)


def map_to_int_range(values, target_min=1, target_max=10):
  """Maps a list into the integer range from target_min to target_max
     Pass a list of floats, returns the list as ints
     The 2 lists are zippable"""
  integer_values = []
  values_ordered = sorted(values)
  min_value = float(values_ordered[0])
  max_value = float(values_ordered[-1])

  if min_value == max_value:
    #convert to integer and clamp between min and max
    integer_value = int(min_value)
    integer_value = max(target_min, integer_value)
    integer_value = min(integer_value, target_max)
    return [integer_value for v in values]

  target_range = (target_max - target_min)
  float_range = (max_value - min_value)
  for value in values:
    value = target_min + int(target_range * ((value - min_value) / float_range))
    integer_values.append(value)
  return integer_values


def get_angle(ttfont):
  """Returns the italic angle, given a filename of a TTF"""
  return ttfont['post'].italicAngle



FONT_SIZE=30
# The text used to test weight and width. Note that this could be
# problematic if a given font doesn't have latin support.
LATIN_TEXT = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvXxYyZz"
KHMER_TEXT = "\xE1\x9E\x9A\xE1\x9E\x9B\xE1\x9E\x80\xE1\x9E\x94\xE1\x9E\x80\xE1\x9F\x8B\xE1\x9E\x94\xE1\x9F\x84\xE1\x9E\x80\xE1\x9E\x93\xE1\x9E\xB6\xE1\x9E\x9B\xE1\x9F\x92\xE1\x9E\x84\xE1\x9E\xB6\xE1\x9E\x85\xE1\x9E\x8A\xE1\x9F\x8F\xE1\x9E\x80\xE1\x9E\x8E\xE1\x9F\x92\xE1\x9E\x8F\xE1\x9F\x84\xE1\x9E\x85\xE1\x9E\x80\xE1\x9E\x8E\xE1\x9F\x92\xE1\x9E\x8F\xE1\x9F\x82\xE1\x9E\x84"


img_counter=0
def render_single_line(fontfile, khmer=False):
  global img_counter

  if khmer:
    sample_text = KHMER_TEXT
  else:
    sample_text = LATIN_TEXT

  face = create_cairo_font_face_for_file(fontfile, 0)

  #dummy surface
  surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
  ctx = cairo.Context(surface)
  ctx.set_font_face(face)
  ctx.set_font_size(30)
  extents = ctx.text_extents(sample_text)
#  print extents
  xbearing, ybearing, width, height, _, _ = extents


  #actual surface
  surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
  ctx = cairo.Context(surface)

  ctx.set_font_face(face)
  ctx.set_font_size(30)
  ctx.move_to(-xbearing, -ybearing)
  ctx.show_text(sample_text)

  del ctx

  img_counter += 1
  try:
    surface.write_to_png("font_classification_tool/images/{}.png".format(img_counter))
    return "<img height='50%%' src='font_classification_tool/images/{}.png' />".format(img_counter)
  except:
    print ("Cairo failed to write PNG file for {}".format(fontfile))
    return ""

def get_base64_image(img):
  """Get the base 64 representation of an image,
     to use for visual testing."""
  output = StringIO.StringIO()
  img.save(output, "PNG")
  base64img = output.getvalue().encode("base64")
  output.close()
  return base64img



def main():
  args = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(-1)

  files_to_process = []
  for pattern in args.files:
    files_to_process.extend(glob.glob(pattern))

  if len(files_to_process) == 0:
    sys.exit("No font files were found!")

  fontinfo = {}
  # start with the existing values:
  if args.existing:
    with open(args.existing) as csvfile:
        existing_data = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(existing_data) # skip first row as its not data
        for row in existing_data:
          gfn = row[0]
          fontinfo[gfn] = {
            "weight_int": int(row[1]),
            "angle_int": int(row[2]),
            "width_int": int(row[3]),
            "usage": row[4],
            "subsets": row[5],
            "gfn": gfn,
            "img_weight": None
          }

  for fname in files_to_process:
    gfn = GFN_from_filename(fname)
    if gfn in fontinfo.keys():
      fontinfo[gfn]['img_weight'] = render_single_line(fname, "khmer" in fontinfo[gfn]['subsets'])
      # TODO: fontinfo[gfn]["weight"]
      # TODO: "width" = width
      # TODO: "angle" = angle

  # analyse_fonts(files_to_process)

  if fontinfo == {}:
    sys.exit("All specified fonts are blacklisted!")



  # generate data for the web server
  # double(<unit>, <precision>, <decimal_point>, <thousands_separator>, <show_unit_before_number>, <nansymbol>)
  grid_data = {
    "metadata": [
      {"name":"fontfile","label":"filename","datatype":"string","editable":True},
      {"name":"gfn","label":"GFN","datatype":"string","editable":True},
      {"name":"weight","label":"weight","datatype":"double(, 2, dot, comma, 0, n/a)","editable":True},
      {"name":"weight_int","label":"WEIGHT_INT","datatype":"integer","editable":True},
      {"name":"width","label":"width","datatype":"double(, 2, dot, comma, 0, n/a)","editable":True},
      {"name":"width_int","label":"WIDTH_INT","datatype":"integer","editable":True},
      {"name":"usage","label":"USAGE","datatype":"string","editable":True,
        "values": {"header":"header", "body":"body", "unknown":"unknown"}
      },
      {"name":"angle","label":"angle","datatype":"double(, 2, dot, comma, 0, n/a)","editable":True},
      {"name":"angle_int","label":"ANGLE_INT","datatype":"integer","editable":True},
      {"name":"image","label":"image","datatype":"html","editable":False},
    ],
    "data": []
  }
  #generate_italic_angle_images()

  field_id = 1
  for key in fontinfo:
    values = fontinfo[key]
    img_weight_html = ""
    if values["img_weight"] is not None:
      img_weight_html = values["img_weight"]
    #  img_weight_html = "<img height='50%%' src='data:image/png;base64,%s' />" % (values["img_weight"])

    values["image"] = img_weight_html
    grid_data["data"].append({"id": field_id, "values": values})
    field_id += 1

  def save_csv():
    filename = args.output
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', lineterminator='\n')
        writer.writerow(["GFN","FWE","FIA","FWI","USAGE"]) # first row has the headers
        for data in sorted(grid_data['data'], key=lambda d: d['values']['gfn']):
          values = data['values']
          gfn = values['gfn']
          fwe = values['weight_int']
          fia = values['angle_int']
          fwi = values['width_int']
          usage = values['usage']
          writer.writerow([gfn, fwe, fia, fwi, usage])
    return 'ok'

  app = Flask(__name__)
  @app.route('/font_classification_tool/<path:path>')
  def send_the_files(path):
    print (path)
    if path == 'index.html' or path.endswith('.js'):
      return send_from_directory(os.path.dirname(__file__) + '/font_classification_tool/', path)
    else:
      return send_from_directory(os.path.dirname(__file__), path)

  @app.route('/data.json')
  def json_data():
    return jsonify(grid_data)

  @app.route('/update', methods=['POST'])
  def update():
    rowid = request.form['id']
    newvalue = request.form['newvalue']
    colname = request.form['colname']
    for row in grid_data["data"]:
      if row['id'] == int(rowid):
        row['values'][colname] = newvalue
    return save_csv()

#  if blacklisted:
#    print ("{} blacklisted font files:\n".format(len(blacklisted)))
#    print ("".join(map("* {}\n".format, blacklisted)))

#  if bad_darkness:
#    print ("Failed to detect weight(darkness value) for {} of the font files:\n".format(len(bad_darkness)))
#    print ("".join(map("* {}\n".format, bad_darkness)))

  print ("\n\nAccess http://127.0.0.1:5000/font_classification_tool/index.html\n")
  app.run()


if __name__ == "__main__":
  main()
