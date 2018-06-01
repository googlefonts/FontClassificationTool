# Font Classification Tool

This tool helps maintain the "font metadata" used by Google Fonts. 

The canonical copy of this metadata is <https://github.com/google/fonts/blob/master/tools/font-metadata.csv>

This tool has two parts

1. A web UI for manually maintaining the data
2. A python server for auto-detecting some values, serving the web UI with them, and saving new CSV 

## Installation

### macOS

    brew install python2;
    pip2 install flask;

## Usage

    ./font-classification-tool.py \
      --existing=font-metadata.csv \
      ~/fonts/*/*/*.ttf \
      -o output.csv;
