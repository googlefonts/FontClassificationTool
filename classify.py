#!/usr/bin/env python2
import argparse
import sys
import glob
from gfn import (GFNs_from_filenames,
                 GFN_from_filename)
from util import (group_by_weight,
                  save_csv,
                  read_csv,
                  is_blacklisted)

DESCRIPTION = "Compute the weight value for all given font files."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-f", "--files", default="*", required=True, nargs="+",
                    help="The pattern to match for finding ttfs, eg 'folder_with_fonts/*.ttf'.")
parser.add_argument("-o", "--output", default="output.csv", required=True,
                    help="CSV metadata output filename")
parser.add_argument("-i", "--input", default="input.csv", required=True,
                    help="CSV metadata input filename")

def main():
  args = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(-1)

  files_to_process = []
  for pattern in args.files:
    files_to_process.extend(glob.glob(pattern))

  old_metadata = read_csv(args.input)
  print("There are {} entries in the old metadata CSV.".format(len(old_metadata.keys())))

  blacklisted = [fname for fname in files_to_process if is_blacklisted(fname)]
  files_to_process = [fname for fname in files_to_process if not is_blacklisted(fname) and \
                                                             GFN_from_filename(fname) in old_metadata.keys()]

  if blacklisted:
    print ("{} font files were blacklisted:\n".format(len(blacklisted)))
    print ("".join(map("* {}\n".format, blacklisted)))

  if len(files_to_process) == 0:
    sys.exit("Nothing to do! Aborting.")
  else:
    print("Will process {} font files.".format(len(files_to_process)))


  weights = group_by_weight(files_to_process)
  GFNs = GFNs_from_filenames(files_to_process)

  metadata = {}
  for fname in files_to_process:
    gfn = GFNs[fname]
    if gfn in old_metadata.keys():
      metadata[gfn] = old_metadata[gfn] # preserve every old value
      metadata[gfn]['weight_int'] = weights[fname] # except the new weight values we have just computed

#  for gfn in sorted(metadata.keys()):
#    print("{}: {}".format(gfn, metadata[gfn]['weight_int']))

  if args.output:
    save_csv(args.output, metadata)


if __name__ == "__main__":
  main()
