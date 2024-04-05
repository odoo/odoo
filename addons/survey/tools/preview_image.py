# Part of Odoo. See LICENSE file for full copyright and licensing details.

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import base64_to_image, file_path

FONT = ImageFont.truetype(file_path("web/static/fonts/google/Montserrat/Montserrat-SemiBold.ttf"), 32)
FONT_BOLD = ImageFont.truetype(file_path("web/static/fonts/google/Montserrat/Montserrat-Bold.ttf"), 64)
FONT_BOLD_LARGE = FONT_BOLD.font_variant(size=80)
OG_WIDTH, OG_HEIGHT = 1200, 630  # Open Graph
PADDING = 80  # Padding around the preview's content
SECONDARY_IMAGE_SIZE = 40
SPACER = 12  # Spacing between elements
BOTTOM_TEXT_LINE_Y = OG_HEIGHT - PADDING - FONT.size

def generate_survey_preview_image(background_image, kpis, secondary_image, secondary_text,
                                  tag_description, tag_path, title):
    """Create the image used inside link previews.
    The image is created on the fly so that we don't need to store it.
    """

    image = Image.new('RGBA', (OG_WIDTH, OG_HEIGHT), color="white")
    d = ImageDraw.Draw(image)

    # Use the background image as the preview's background if there is one
    if background_image:
        # Darken background image
        enhancer = ImageEnhance.Brightness(background_image)
        background_image = enhancer.enhance(0.4)
        # Resize background image while keeping the ratio
        background_image = background_image.resize((OG_WIDTH, int(background_image.height * OG_WIDTH / background_image.width)))
        image.paste(background_image)
        # Recolor texts to make them readable on darkened image
        font_color = "#F8F7F7"
        font_color_light = "#D4D1CD"
        font_color_brand = font_color_light
    else:
        font_color = "#333333"
        font_color_light = "#666666"
        font_color_brand = "#714B67"
        # Decorative Odoo logo's "O" (top right)
        d.ellipse((OG_WIDTH - 274, -274, OG_WIDTH + 274, 274), fill=None, outline="#EFEBEE", width=112)

    # Tag and title
    icon = Image.open(file_path(tag_path)).convert("RGBA")
    image.paste(icon, (PADDING, PADDING), icon)
    d.text((PADDING + icon.width + SPACER, PADDING), tag_description, font=FONT, fill=font_color_brand)
    d.text((PADDING, PADDING + icon.height + SPACER), wrap_to_pixels(title, OG_WIDTH - 2 * PADDING, FONT_BOLD), font=FONT_BOLD, fill=font_color)

    # Secondary image and text
    secondary_image = secondary_image.resize((SECONDARY_IMAGE_SIZE, SECONDARY_IMAGE_SIZE))
    mask = Image.new("RGBA", (SECONDARY_IMAGE_SIZE, SECONDARY_IMAGE_SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SECONDARY_IMAGE_SIZE, SECONDARY_IMAGE_SIZE), fill="white", outline=None, width=4, radius=8)
    image.paste(secondary_image, (PADDING, BOTTOM_TEXT_LINE_Y), mask)
    d.text((PADDING + SECONDARY_IMAGE_SIZE + SPACER, BOTTOM_TEXT_LINE_Y), secondary_text, font=FONT, fill=font_color_light)

    # "Powered by Odoo"
    logo = Image.open(file_path(f"web/static/img/logo{'-white' if background_image else ''}.png"))
    logo.thumbnail((OG_WIDTH / 6, SECONDARY_IMAGE_SIZE))
    logo_position_x = OG_WIDTH - PADDING - logo.width
    image.paste(logo, (logo_position_x, BOTTOM_TEXT_LINE_Y), logo.convert("RGBA"))
    powered_by_string = _("Powered by")
    d.text((logo_position_x - SPACER - FONT.getlength(powered_by_string), BOTTOM_TEXT_LINE_Y), powered_by_string, font=FONT, fill=font_color_light)

    # KPIs
    for x, (kpi_label, kpi_value) in zip((PADDING, 460, 840), kpis):
        d.text((x, 400), kpi_label, font=FONT, fill=font_color_light)
        d.text((x, 300), kpi_value, font=FONT_BOLD_LARGE, fill=font_color)

    return image

def get_image(image_field_value):
    """Return Image from field value"""
    if not image_field_value:
        return
    try:
        return base64_to_image(image_field_value)
    except UserError:
        # E.g., with vector images formats that PIL does not support
        return

def wrap_to_pixels(text, max_length, font, max_n_lines=2):
    """Breaks the given text in multiple lines to not overflow the given max_length.
    Different from textwrap because it limits the length in pixels, not in characters.
    """
    text_lines = ['']
    for word in text.split():
        line = f"{text_lines[-1]} {word}"
        if font.getlength(line) <= max_length:
            text_lines[-1] = line
        elif len(text_lines) == max_n_lines:
            text_lines[-1] += "..."
            break
        else:
            text_lines.append(word)
    return "\n".join(text_lines).strip()
