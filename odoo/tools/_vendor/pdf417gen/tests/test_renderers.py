from pdf417gen import render_svg, render_image, encode
from pdf417gen.rendering import barcode_size, rgb_to_hex
from PIL.Image import Image
from xml.etree.ElementTree import ElementTree

codes = encode("hello world!")


def modules(codes):
    """Iterates over barcode codes and yields barcode moudles.

    Yields: column number (int), row number (int), module visibility (bool).
    """

    for row_id, row in enumerate(codes):
        col_id = 0
        for value in row:
            for digit in format(value, 'b'):
                yield col_id, row_id, digit == "1"
                col_id += 1


def test_rgb_to_hex():
    assert rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert rgb_to_hex((0, 255, 0)) == "#00ff00"
    assert rgb_to_hex((0, 0, 255)) == "#0000ff"

    assert rgb_to_hex((100, 0, 0)) == "#640000"
    assert rgb_to_hex((0, 100, 0)) == "#006400"
    assert rgb_to_hex((0, 0, 100)) == "#000064"

    assert rgb_to_hex((111, 222, 32)) == "#6fde20"


def test_render_svg():
    scale = 2
    ratio = 4
    description = "hi there"

    tree = render_svg(codes, scale=scale, ratio=ratio, description=description)
    assert isinstance(tree, ElementTree)
    assert tree.findtext("description") == description

    # Test expected size
    width, height = barcode_size(codes)

    root = tree.getroot()

    assert root.get("width") == str(width * scale)
    assert root.get("height") == str(height * scale * ratio)
    assert root.get("version") == "1.1"
    assert root.get("xmlns") == "http://www.w3.org/2000/svg"

    # Check number of rendered modules (only visible ones)
    expected_module_count = len([v for x, y, v in modules(codes) if v])
    actual_module_count = len(root.findall('g/rect'))

    assert expected_module_count == actual_module_count


def test_render_image():
    width, height = barcode_size(codes)

    image = render_image(codes)
    assert isinstance(image, Image)

    image = render_image(codes, scale=1, ratio=1, padding=0)
    assert image.size == (width, height)

    image = render_image(codes, scale=2, ratio=1, padding=0)
    assert image.size == (2 * width, 2 * height)

    image = render_image(codes, scale=2, ratio=2, padding=0)
    assert image.size == (2 * width, 4 * height)

    image = render_image(codes, scale=2, ratio=2, padding=20)
    assert image.size == (2 * width + 40, 4 * height + 40)

    # Check actual pixels
    fg_color = "LemonChiffon"
    bg_color = "#aabbcc"

    fg_parsed = (255, 250, 205)
    bg_parsed = (170, 187, 204)

    image = render_image(codes, scale=1, ratio=1, padding=0,
                         fg_color=fg_color, bg_color=bg_color)
    px = image.load()

    for column, row, visible in modules(codes):
        expected = fg_parsed if visible else bg_parsed
        assert px[column, row] == expected
