# PDF Image Extractor

## Overview

The PDF Image Extractor is a Python script designed to process PDF files, specifically extracting and saving images embedded within the pages of the document. Besides the image extraction, it also prints out the textual content of the pages. This tool can be particularly useful when handling digital catalogs or any PDFs with important embedded images.

## Features

- **Image Extraction**: Efficiently extracts images from any page within a provided PDF. Images smaller than 500x500 pixels are skipped.
- **Image Resizing**: Automatically resizes the extracted images to 70% of their original size, ensuring consistent output and potentially reducing file size.
- **Text Extraction**: For each processed page, the script also extracts and prints the textual content.
- **Flexibility**: Designed with modularity in mind, making it easy to integrate, expand, or modify for various use cases.

## Requirements

To run this script, you will need:

- Python 3.x
- pdfplumber
- fitz (PyMuPDF)
- PIL (Pillow)

These can be installed using `pip`:

```
pip install pdfplumber pymupdf pillow
```

or if using [uv](https://docs.astral.sh/uv/)

```
uv sync
uv run main.py input_file output_dir img_format img_quality
```

## Usage

1. Clone the repository or download the script.
2. Run the script:
```
python main.py input_file output_dir img_format img_quality
```

The arguments are:

- `input_file`: path to the PDF to process.
- `output_dir`: where the extracted images are written. It is created if it does not exist.
- `img_format`: output format, e.g. `webp`, `png`, `jpg`. Any format Pillow can write is accepted.
- `img_quality`: compression quality, from 1 to 100. Ignored by formats that are always lossless, such as PNG.

For example, you can extract to png in the current folder via:

```
python main.py ./file.pdf ./ png 100
```

Images are named after the digits found in the text of the page they come from, followed by the page number — for example `12345-_7.png`. When a page holds more than one image, the second and later files get an extra counter (`12345-_7_2.png`).

## Customization

- **Changing Output Image Format**: Pass the format you want as the `img_format` argument; `webp` is a good default due to its efficiency.
- **Adjusting Resizing Ratio**: The `resize_image` function currently reduces the image size to 70% of the original. Adjust the resizing ratio as per your requirements by modifying the multiplier value.
- **Adjusting the Size Filter**: `save_images_from_page` skips images narrower or shorter than 500 pixels, which filters out logos and icons. Change that threshold if you need the smaller images too.
