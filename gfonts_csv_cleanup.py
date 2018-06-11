#!/usr/bin/env python
import sys
from util import read_csv, save_csv

import argparse
DESCRIPTION = "Cleanup CSV prior to pushing it to GFonts staging servers."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument("-m", "--metadata", default="input.csv", required=True,
                    help="CSV metadata filename")


def main():
  args = parser.parse_args()

  if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(-1)

  metadata = read_csv(args.metadata)
  save_csv(args.metadata, metadata, cleanup_for_publishing=True)

if __name__ == "__main__":
  main()
