#!/usr/bin/env python3
import sys
from util import read_csv, save_csv
from gfn import get_GFNs_from_gfonts

import argparse
DESCRIPTION = "Update GFNs on an old metadata CSV based on the font files currently hosted on Google Fonts."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-m", "--metadata", default="input.csv", required=True,
                    help="CSV metadata filename")
parser.add_argument("-k", "--apikey", required=True,
                    help="Google Fonts API key")
parser.add_argument("-n", "--addnew", action='store_true',
                    help="Add new fonts")


def main():
  args = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(-1)

  # we start by loading the contents of the old metadata file:
  metadata = read_csv(args.metadata)

  # and getting a list of what's currently available on Google Fonts:
  gfonts_GFNs = get_GFNs_from_gfonts(args.apikey)

  # Then we remove the fonts that are not on GFonts nowadays:
  for gfn in metadata.keys():
    if gfn not in gfonts_GFNs:
      del metadata[gfn]

  # and add the ones that are not yet listed on the old metadata csv:
  if args.addnew:
    for gfn in gfonts_GFNs.keys():
      if gfn not in metadata:
        metadata[gfn] = {
          'weight_int': -1,
          'width_int': -1,
          'angle_int': -1,
          'usage': '?',
        }

  # and update the subsets field:
  for gfn in gfonts_GFNs.keys():
    if gfn in metadata:
      subsets = gfonts_GFNs[gfn]
      metadata[gfn]['subsets'] = "+".join(sorted(subsets))

  # done:
  save_csv(args.metadata, metadata)

if __name__ == "__main__":
  main()
