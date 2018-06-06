#!/usr/bin/env python3
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
import os
import sys
import collections
from fonts_public_pb2 import FamilyProto
from constants import (NAMEID_FONT_FAMILY_NAME,
                       NAMEID_FONT_SUBFAMILY_NAME)

try:
  from fontTools.ttLib import TTFont
except:
  sys.exit("Needs fontTools.\n\npip3 install fonttools")

try:
  from google.protobuf import text_format
except:
  sys.exit("Needs protobuf.\n\npip3 install protobuf")


def get_FamilyProto_Message(path):
    message = FamilyProto()
    text_data = open(path, "rb").read()
    text_format.Merge(text_data, message)
    return message


# The canonical [to Google Fonts] name comes before any aliases
_KNOWN_WEIGHTS = collections.OrderedDict([
    ('Thin', 100),
    ('Hairline', 100),
    ('ExtraLight', 200),
    ('Light', 300),
    ('Regular', 400),
    ('', 400),  # Family-Italic resolves to this
    ('Medium', 500),
    ('SemiBold', 600),
    ('Bold', 700),
    ('ExtraBold', 800),
    ('Black', 900)
])

FileFamilyStyleWeightTuple = collections.namedtuple(
    'FileFamilyStyleWeightTuple', ['file', 'family', 'style', 'weight'])


def StyleWeight(styleweight):
  """Breaks apart a style/weight specifier into a 2-tuple of (style, weight).

  Args:
    styleweight: style/weight string, e.g. Bold, Regular, or ExtraLightItalic.
  Returns:
    2-tuple of style (normal or italic) and weight.
  """
  if styleweight.endswith('Italic'):
    return ('italic', _KNOWN_WEIGHTS[styleweight[:-6]])

  return ('normal', _KNOWN_WEIGHTS[styleweight])


def FamilyName(fontname):
  """Attempts to build family name from font name.

  For example, HPSimplifiedSans => HP Simplified Sans.

  Args:
    fontname: The name of a font.
  Returns:
    The name of the family that should be in this font.
  """
  # SomethingUpper => Something Upper
  fontname = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', fontname)
  # Font3 => Font 3
  fontname = re.sub('([a-z])([0-9]+)', r'\1 \2', fontname)
  # lookHere => look Here
  return re.sub('([a-z0-9])([A-Z])', r'\1 \2', fontname)


class ParseError(Exception):
  """Exception used when parse failed."""


def FileFamilyStyleWeight(filename):
  """Extracts family, style, and weight from Google Fonts standard filename.

  Args:
    filename: Font filename, eg Lobster-Regular.ttf.
  Returns:
    FileFamilyStyleWeightTuple for file.
  Raises:
    ParseError: if file can't be parsed.
  """

  m = re.search(r'([^/-]+)-(\w+)\.ttf$', filename) #FAMILY_WEIGHT_REGEX
  if not m:
    raise ParseError('Could not parse %s' % filename)

  sw = StyleWeight(m.group(2))
  return FileFamilyStyleWeightTuple(filename,
                                    FamilyName(m.group(1)),
                                    sw[0],
                                    sw[1])


def _FileFamilyStyleWeights(fontdir):
  """Extracts file, family, style, weight 4-tuples for each font in dir.

  Args:
    fontdir: Directory that supposedly contains font files for a family.
  Returns:
    List of FileFamilyStyleWeightTuple ordered by weight, style
    (normal first).
  Raises:
    OSError: If the font directory doesn't exist (errno.ENOTDIR) or has no font
    files (errno.ENOENT) in it.
    RuntimeError: If the font directory appears to contain files from multiple
    families.
  """
  if not os.path.isdir(fontdir):
    raise OSError(errno.ENOTDIR, 'No such directory', fontdir)

  files = glob.glob(os.path.join(fontdir, '*.ttf'))
  if not files:
    raise OSError(errno.ENOENT, 'no font files found')

  result = [FileFamilyStyleWeight(f) for f in files]
  def _Cmp(r1, r2):
    return cmp(r1.weight, r2.weight) or -cmp(r1.style, r2.style)
  result = sorted(result, _Cmp)

  family_names = {i.family for i in result}
  if len(family_names) > 1:
    raise RuntimeError('Ambiguous family name; possibilities: %s'
                       % family_names)

  return result


def GFN_from_filename(fontfile):
  ttfont = TTFont(fontfile)

  gfn = "unknown"
  fontdir = os.path.dirname(fontfile)
  metadata = os.path.join(fontdir, "METADATA.pb")
  if os.path.exists(metadata):
    family = get_FamilyProto_Message(metadata)
    for font in family.fonts:
      if font.filename in fontfile:
        gfn = "{}:{}:{}".format(family.name, font.style, font.weight)
        break
  else:
    try:
      attributes = _FileFamilyStyleWeights(fontdir)
      for (fontfname, family, style, weight) in attributes:
        if fontfname in fontfile:
          gfn = "{}:{}:{}".format(family, style, weight)
          break
    except:
      pass

  if gfn == 'unknown':
    #This font lacks a METADATA.pb file and also failed
    # to auto-detect the GFN value. As a last resort
    # we'll try to extract the info from the NAME table entries.
    try:
      for entry in ttfont['name'].names:
        if entry.nameID == NAMEID_FONT_FAMILY_NAME:
          family = entry.string.decode(entry.getEncoding()).encode('ascii', 'ignore').strip()
        if entry.nameID == NAMEID_FONT_SUBFAMILY_NAME:
          style, weight = StyleWeight(entry.string.decode(entry.getEncoding()).encode('ascii', 'ignore').strip())
      ttfont.close()
      if family != "": #avoid empty string in cases of misbehaved family names in the name table
        gfn = "{}:{}:{}".format(family, style, weight)
        if VERBOSE:
          print ("Detected GFN from name table entries: '{}' (file='{}')".format(gfn, fontfile))
    except:
      print("This seems to be a really bad font file...")
      pass

  if gfn == 'unknown':
    print ("Failed to detect GFN value for '{}'. Defaults to 'unknown'.".format(fontfile))

  return gfn

def GFNs_from_filenames(filenames):
  return {fname: GFN_from_filename(fname) for fname in filenames}

