#!/usr/bin/env python2
import argparse
import sys
import glob
from util import group_by_weight, save_csv
from gfn import GFNs_from_filenames

DESCRIPTION = "Compute the weight value for all given font files."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-f", "--files", default="*", required=True, nargs="+",
                    help="The pattern to match for finding ttfs, eg 'folder_with_fonts/*.ttf'.")
parser.add_argument("-o", "--output", default="output.csv", required=True,
                    help="CSV data output filename")

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

  weights = group_by_weight(files_to_process)
  GFNs = GFNs_from_filenames(files_to_process)


  metadata = {GFNs[fname]: {'weight_int': weights[fname],
                            'width_int': -1,
                            'angle_int': -1,
                            'usage': '?',
                           } for fname in files_to_process}

  for gfn in sorted(metadata.keys()):
    print("{}: {}".format(gfn, metadata[gfn]['weight_int']))

  if args.output:
    save_csv(args.output, metadata)


if __name__ == "__main__":
  main()
