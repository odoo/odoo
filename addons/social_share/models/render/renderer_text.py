import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from odoo import _, models
from odoo.exceptions import UserError
from .image_render_utils import get_rgb_from_hex, TypedText, TypedString
from .renderer import FieldRenderer, Renderer


_logger = logging.getLogger(__name__)

class TextRenderer(Renderer):
    text_align_horizontal: str
    text_align_vertical: str
    text_color: tuple[int, int, int]
    text_fonts: list[models.Model]
    text_font_size: int

    def __init__(
            self,
            *args,
            text_align_horizontal=None,
            text_align_vertical='center',
            text_color: str = 'ffffff',
            text_fonts=None,
            text_font_size=16,
            **kwargs):
        super().__init__(
            self,
            *args,
            text_align_horizontal=text_align_horizontal,
            text_align_vertical=text_align_vertical,
            text_color=text_color,
            text_fonts=text_fonts,
            text_font_size=text_font_size,
            **kwargs
        )
        if text_align_horizontal is None:
            text_align_horizontal = text_align_horizontal if self.size else 'left'
        self.text_align_horizontal = text_align_horizontal
        self.text_align_vertical = text_align_vertical
        self.text_color = get_rgb_from_hex(text_color or 'ffffff')
        self.text_fonts = text_fonts
        self.text_font_size = text_font_size

    def _get_typed_text(self, text):
        """Fetch appropriate fonts for the text and construct a TypedText instance.

        :param text str:
        :returns TypedText:
        """
        def _char_in_range(char, ranges):
            for low_bound, top_bound in zip(ranges[::2], ranges[1::2]):
                if char >= low_bound and char <= top_bound:
                    return True
            return False

        text_fonts = self.text_fonts.sorted(lambda font: (bool(font.character_ranges), font.sequence, font.id))
        fonts = list(zip(text_fonts, text_fonts.mapped('character_ranges')))
        font, font_char_ranges = fonts[0]
        font_string_groups = []
        for char in text:
            char_in_cmap = _char_in_range(char, font_char_ranges)
            if font_string_groups and char_in_cmap:
                font_string_groups[-1][1].append(char)
                continue

            font_found = False
            if char != '\n':
                for font, font_char_ranges in fonts:
                    # if not characters, we've already gone through the ones that had a character map
                    # so we now have to hope this one contains the character
                    if not font.character_ranges or _char_in_range(char, font_char_ranges):
                        font_string_groups.append((font, [char]))
                        font_found = True
                        break
                else:
                    _logger.warning("Could not find a font for '%c'", char)
            if not font_found:
                font = font_char_ranges = []
                if font_string_groups and font_string_groups[-1][0] is None:
                    font_string_groups[-1][1].append(char)
                else:
                    font_string_groups.append((None, [char]))
        return TypedText.from_typed_strings([
            TypedString(
                ImageFont.truetype(BytesIO(font.raw), font.force_font_size or self.text_font_size) if font is not None else None,
                ''.join(chars),
                resize_ratio=(self.text_font_size / font.force_font_size) if font and font.force_font_size else 1,
            ) for font, chars in font_string_groups])

    def get_text(self, *args, **kwargs):
        return ''

    def render_image(self, *args, record=None, **kwargs):
        text = self.get_text(record=record)
        if not text or not self.text_fonts:
            return None
        typed_text = self._get_typed_text(text).align(((0, 0), self.size), self.text_align_horizontal or 'left')
        if self.size[1] and (typed_text.height > self.size[1]):
            raise UserError(_('The text "%(text)s" cannot fit in the requested height %(height)d', text=text, height=self.size[1]))
        base_image = Image.new('RGBA', (max(self.size[0], typed_text.width), max(self.size[1], typed_text.height)), color=(0, 0, 0, 0))
        editor = ImageDraw.ImageDraw(base_image)
        for line in typed_text.lines:
            x_offset = 0
            for string in line.strings:
                if string.font is None:
                    continue
                if string.resize_ratio != 1:
                    intermediate_image = Image.new('RGBA', string.preresize_size, color=(0, 0, 0, 0))
                    intermediate_image_editor = ImageDraw.ImageDraw(intermediate_image)
                    intermediate_image_editor.text((0, 0), string.text, font=string.font, fill=self.text_color, embedded_color=True)
                    resized_intermediate = intermediate_image.resize(
                        (string.width, string.height),
                        Image.LANCZOS,
                    )
                    base_image.paste(resized_intermediate, (line.pos[0] + x_offset, line.pos[1]), resized_intermediate)
                else:
                    editor.text((line.pos[0] + x_offset, line.pos[1]), string.text, font=string.font, fill=self.text_color, embedded_color=True)
                x_offset += string.width
        return base_image

class UserTextRenderer(TextRenderer):
    text: str

    def __init__(self, *args, text='', **kwargs):
        self.text = text or ''
        super().__init__(self, *args, text=text, **kwargs)

    def get_text(self, *args, **kwargs):
        return self.text or ''


class FieldTextRenderer(TextRenderer, FieldRenderer):
    def get_text(self, record=None):
        field_value = self.get_field_value(record=record)
        if not field_value:
            field_name = self.get_field_name(record=record)
            return f'[{field_name}]' if field_name else None
        return field_value
