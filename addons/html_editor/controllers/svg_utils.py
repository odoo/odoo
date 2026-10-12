import re
from os.path import join as opj

import werkzeug.exceptions
from lxml import etree

from odoo import tools
from odoo.tools.image import binary_to_image, get_webp_size, image_data_uri
from odoo.tools.misc import file_open


def get_shape_svg(module, *segments):
    shape_path = opj(module, 'static', *segments)
    try:
        with file_open(shape_path, 'r', filter_ext=('.svg',)) as file:
            return file.read()
    except FileNotFoundError:
        raise werkzeug.exceptions.NotFound()


def update_svg_colors(env, options, svg):
    user_colors = []
    svg_options = {}
    default_palette = {
        '1': '#3AADAA',
        '2': '#7C6576',
        '3': '#F6F6F6',
        '4': '#FFFFFF',
        '5': '#383E45',
    }
    bundle_css = None
    regex_hex = r'#[0-9A-F]{6,8}'
    regex_rgba = r'rgba?\(\d{1,3}, ?\d{1,3}, ?\d{1,3}(?:, ?[0-9.]{1,4})?\)'
    for key, value in options.items():
        color_match = re.match(r'^c([1-5])$', key)
        if color_match:
            css_color_value = value
            # Check that color is hex or rgb(a) to prevent arbitrary injection
            if not re.match(r'(?i)^%s$|^%s$' % (regex_hex, regex_rgba), css_color_value.replace(' ', '')):
                if re.match(r'^o-color-([1-5])$', css_color_value):
                    if not bundle_css:
                        bundle = 'web.assets_frontend'
                        asset = env["ir.qweb"]._get_asset_bundle(bundle)
                        bundle_css = asset.css().index_content
                    color_search = re.search(r'(?i)--%s:\s+(%s|%s)' % (css_color_value, regex_hex, regex_rgba), bundle_css)
                    if not color_search:
                        raise werkzeug.exceptions.BadRequest()
                    css_color_value = color_search.group(1)
                else:
                    raise werkzeug.exceptions.BadRequest()
            user_colors.append([tools.html_escape(css_color_value), color_match.group(1)])
        else:
            svg_options[key] = value

    color_mapping = {default_palette[palette_number]: color for color, palette_number in user_colors}
    # create a case-insensitive regex to match all the colors to replace, eg: '(?i)(#3AADAA)|(#7C6576)'
    regex = '(?i)%s' % '|'.join('(%s)' % color for color in color_mapping)

    def subber(match):
        key = match.group().upper()
        return color_mapping.get(key, key)
    return re.sub(regex, subber, svg), svg_options


def make_shaped_image(env, svg, image, mimetype, options):
    if mimetype == "image/webp":
        width, height = (str(size) for size in get_webp_size(image))
    else:
        img = binary_to_image(image)
        width, height = (str(size) for size in img.size)
    root = etree.fromstring(svg)

    # When data-aspect-ratio-crop is set in the shape SVG, it means that we
    # want to crop the image to fit the shape aspect ratio and fill the
    # entire shape.
    if root.attrib.get("data-aspect-ratio-crop") and \
            (image_elem := root.find('.//svg:image', {'svg': 'http://www.w3.org/2000/svg'})) is not None:
        # We set the image width and height to 100% to make it fill the
        # entire shape, and use preserveAspectRatio to crop it if needed.
        image_elem.attrib.update({
            'width': '100%',
            'height': '100%',
            'preserveAspectRatio': 'xMidYMid slice',
        })

    if root.attrib.get("data-forced-size") or root.attrib.get("data-aspect-ratio-crop"):
        # Adjusts the SVG height to ensure the image fits properly within
        # the SVG (e.g. for "devices" shapes and shapes that need to keep
        # their aspect ratio).
        svg_height = float(root.attrib.get("height"))
        svg_width = float(root.attrib.get("width"))
        svg_aspect_ratio = svg_width / svg_height
        height = str(float(width) / svg_aspect_ratio)

    root.attrib.update({'width': width, 'height': height})
    # Update default color palette on shape SVG.
    svg, _ = update_svg_colors(env, options, etree.tostring(root, pretty_print=True).decode('utf-8'))
    # Add image in base64 inside the shape.
    uri = image_data_uri(image)
    return svg.replace('<image xlink:href="', '<image xlink:href="%s' % uri)
