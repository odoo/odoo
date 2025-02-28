from PIL import Image, ImageColor, ImageOps
from PIL.Image import Resampling
from xml.etree.ElementTree import ElementTree, Element, SubElement


def barcode_size(codes):
    """Returns the barcode size in modules."""
    num_rows = len(codes)
    num_cols = len(codes[0])

    # 17 bodules per column, last column has an additional module
    width = num_cols * 17 + 1
    height = num_rows

    return width, height


def modules(codes):
    """Iterates over codes and yields barcode moudles as (y, x) tuples."""

    for row_id, row in enumerate(codes):
        col_id = 0
        for value in row:
            for digit in format(value, 'b'):
                if digit == "1":
                    yield col_id, row_id
                col_id += 1


def parse_color(color):
    return ImageColor.getrgb(color)


def rgb_to_hex(color):
    return '#{0:02x}{1:02x}{2:02x}'.format(*color)


def render_image(codes, scale=3, ratio=3, padding=20, fg_color="#000", bg_color="#FFF"):
    width, height = barcode_size(codes)

    # Translate hex code colors to RGB tuples
    bg_color = parse_color(bg_color)
    fg_color = parse_color(fg_color)

    # Construct the image
    image = Image.new("RGB", (width, height), bg_color)

    # Draw the pixle grid
    px = image.load()
    for x, y in modules(codes):
        px[x, y] = fg_color

    # Scale and add padding
    image = image.resize((scale * width, scale * height * ratio), resample=Resampling.NEAREST)
    image = ImageOps.expand(image, padding, bg_color)

    return image


def render_svg(codes, scale=3, ratio=3, color="#000", description=None):
    # Barcode size in modules
    width, height = barcode_size(codes)

    # Size of each module
    scale_x = scale
    scale_y = scale * ratio

    color = rgb_to_hex(parse_color(color))

    root = Element('svg', {
        "version": "1.1",
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(width * scale_x),
        "height": str(height * scale_y),
    })

    if description:
        description_element = SubElement(root, 'description')
        description_element.text = description

    group = SubElement(root, 'g', {
        "id": "barcode",
        "fill": color,
        "stroke": "none"
    })

    # Generate the barcode modules
    for col_id, row_id in modules(codes):
        SubElement(group, 'rect', {
            "x": str(col_id * scale_x),
            "y": str(row_id * scale_y),
            "width": str(scale_x),
            "height": str(scale_y),
        })

    return ElementTree(element=root)
