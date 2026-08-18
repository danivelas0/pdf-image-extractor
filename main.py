import pdfplumber
import fitz
import os
import io
import argparse
from PIL import Image

# The whole page text is used to build filenames, so it has to be capped:
# most filesystems reject a path component longer than 255 characters.
MAX_REFERENCE_LENGTH = 80

# PIL identifies formats by name, not by file extension.
FORMAT_ALIASES = {"JPG": "JPEG", "JPE": "JPEG", "TIF": "TIFF"}

# Parse arguments from terminal
parser=argparse.ArgumentParser(description="The PDF Image Extractor is a Python script designed to process PDF files, specifically extracting and saving images embedded within the pages of the document. Besides the image extraction, it also prints out the textual content of the pages.")
parser.add_argument("input_file")
parser.add_argument("output_dir")
parser.add_argument("img_format")
parser.add_argument("img_quality", type=int)
args=parser.parse_args()

# Define the PDF file path
PDF_PATH = args.input_file
OUTPUT_IMAGES_DIR = args.output_dir
IMAGE_EXTENSION = args.img_format.lower().lstrip(".")
IMAGE_FORMAT = FORMAT_ALIASES.get(IMAGE_EXTENSION.upper(), IMAGE_EXTENSION.upper())
IMAGE_QUALITY = args.img_quality

# Validate the output settings before processing anything, so a typo fails
# immediately instead of halfway through the document.
Image.init()
if IMAGE_FORMAT not in Image.SAVE:
    parser.error(
        f"unsupported image format '{args.img_format}'. "
        f"Supported formats: {', '.join(sorted(Image.SAVE))}")
if not 1 <= IMAGE_QUALITY <= 100:
    parser.error("img_quality must be between 1 and 100")

# The output directory is not guaranteed to exist yet.
os.makedirs(OUTPUT_IMAGES_DIR, exist_ok=True)

# Removes all letters from a string
def remove_letters(text):
    return ''.join([c for c in text if not c.isalpha()])

# Sanitizes a string to be used as a filename
def sanitize_filename(text):
    # Remove invalid filename characters and anything unprintable
    invalid_chars = '<>:"/\\|?*'
    text = ''.join(
        c for c in text
        if c not in invalid_chars and (c.isprintable() or c.isspace()))
    # Collapse every run of whitespace (newlines included) into a single space
    text = ' '.join(text.split())
    # Keep the name short enough to fit in a path component
    text = text[:MAX_REFERENCE_LENGTH]
    # Windows rejects names ending in a space or a dot
    return text.strip(' .')

# Resizes an image so that its width or height does not exceed the specified maximum size.
def resize_image(image):
    """
    Resizes an image so that its width or height does not exceed the specified maximum size.

    Args:
        image: The image to resize.

    Returns:
        The resized image.
    """

    # Calculate the maximum size as 70% of the larger side of the image.
    max_size = int(max(image.width, image.height) * 0.7)

    if image.width > max_size or image.height > max_size:
        if image.width > image.height:
            aspect_ratio = image.height / image.width
            new_width = max_size
            new_height = int(max_size * aspect_ratio)
        else:
            aspect_ratio = image.width / image.height
            new_height = max_size
            new_width = int(max_size * aspect_ratio)

        image = image.resize((new_width, new_height), Image.BICUBIC)
    return image

# Converts an image to a colour mode the target format is able to store.
def convert_for_format(image, image_format):
    """
    Converts an image to a colour mode the target format is able to store.

    PDFs commonly embed CMYK, palette and greyscale images, and neither JPEG
    nor PNG accepts every mode: saving them unchanged raises OSError.

    Args:
        image: The image to convert.
        image_format: The PIL name of the format the image will be saved as.

    Returns:
        The converted image.
    """

    if image_format == "JPEG":
        # JPEG has no alpha channel, so flatten it onto a white background.
        if image.mode in ("RGBA", "LA", "PA") or (
                image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGB", image.size, (255, 255, 255))
            image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1])
            return background
        if image.mode not in ("RGB", "L", "CMYK"):
            return image.convert("RGB")
    elif image.mode == "CMYK":
        # PNG and WEBP cannot store CMYK.
        return image.convert("RGB")
    return image

# Extracts and saves all images from the specified page of the document.
def save_images_from_page(document, page_number, product_reference):
    """
    Extracts and saves all images from the specified page of the document.

    Args:
        document: The PDF document.
        page_number: The page number to extract images from.
        product_reference: The product reference to use for the filenames of the saved images.

    Returns:
        A list of the filenames of the saved images.
    """

    saved_images = []
    pagina = document.load_page(page_number)
    imagens = pagina.get_images(full=True)

    # Pages without usable text leave no reference to name the files after.
    reference = sanitize_filename(product_reference) or "image"
    seen_xrefs = set()

    for img in imagens:
        xref = img[0]
        # The same image can be placed more than once on a single page.
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)

        # A single unreadable image (unsupported codec, broken stream) must
        # not abort the extraction of the rest of the document.
        try:
            base_image = document.extract_image(xref)
            image = Image.open(io.BytesIO(base_image["image"]))
            image.load()
        except Exception as error:
            print(f"Skipped image {xref} on page {page_number + 1}: {error}")
            continue

        # Check size
        if image.width < 500 or image.height < 500:
            continue

        # Resize the image and make it storable in the requested format
        image = convert_for_format(resize_image(image), IMAGE_FORMAT)

        # Set the filename of the image. Every image on a page shares the same
        # reference, so later ones get a suffix instead of overwriting the first.
        suffix = "" if not saved_images else f"_{len(saved_images) + 1}"
        image_filename = os.path.join(
            OUTPUT_IMAGES_DIR,
            f"{reference}_{page_number + 1}{suffix}.{IMAGE_EXTENSION}")

        try:
            image.save(image_filename, IMAGE_FORMAT, quality=IMAGE_QUALITY)
        except OSError as error:
            print(f"Could not save image {xref} on page {page_number + 1}: {error}")
            continue

        saved_images.append(image_filename)

    return saved_images

# Opens the document with fitz for image extraction.
document = fitz.open(PDF_PATH)

try:
    # Uses pdfplumber to extract text and fitz for images.
    with pdfplumber.open(PDF_PATH) as pdf:
        pages = pdf.pages
        for index, pagina in enumerate(pages):
            # Extracts and prints text. Pages without text yield nothing.
            texto = pagina.extract_text() or ""
            print(f"Text on Page {index + 1}:")
            print(texto.strip())
            print("-" * 50)

            # Extracts and saves images.
            imagens = save_images_from_page(
                document, index, remove_letters(texto))
            for img in imagens:
                print(f"Image Saved: {img}")
            print("=" * 50)
finally:
    document.close()
