#!/usr/bin/env python3
import sys
from util import read_csv

import argparse
DESCRIPTION = "Compute some useful stats about the font metadata CSV contents."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-m", "--metadata", default="input.csv", required=True,
                    help="CSV metadata filename")


def main():
  args = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(-1)

  metadata = read_csv(args.metadata)

  stats = {}
  stats['weight'] = {v+1 : len([entry for entry in metadata if metadata[entry]['weight_int'] == v+1]) for v in range(10)}
  stats['width'] = {v+1 : len([entry for entry in metadata if metadata[entry]['width_int'] == v+1]) for v in range(10)}
  stats['angle'] = {v+1 : len([entry for entry in metadata if metadata[entry]['angle_int'] == v+1]) for v in range(10)}
  stats['usage'] = {v : len([entry for entry in metadata if metadata[entry]['usage'] == v]) for v in ['?', 'body', 'header']}

  for field in stats:
    print("\n## {}".format(field))
    for v in stats[field]:
      print("* {}: {}".format(v, stats[field][v]))


if __name__ == "__main__":
  main()
