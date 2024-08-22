import math
from PIL import ImageDraw, Image, ImageFont

class TypedString():
    font: ImageFont.ImageFont
    resize_ratio: float
    text: str
    _size: tuple[int, int] = (0, 0)
    _recompute_size: bool = True

    def __init__(self, font, text, resize_ratio=1):
        self.font = font
        self.resize_ratio = resize_ratio
        self.text = text
        self._recompute_size = True if font else False

    @property
    def preresize_size(self):
        return tuple(self._size)

    @property
    def width(self):
        self._compute_size()
        if self.resize_ratio == 1:
            return self._size[0]
        return math.ceil(self._size[0] * self.resize_ratio)

    @property
    def height(self):
        self._compute_size()
        if self.resize_ratio == 1:
            return self._size[1]
        return math.ceil(self._size[1] * self.resize_ratio)

    def clone(self, text=''):
        return TypedString(self.font, text, resize_ratio=self.resize_ratio)

    def _compute_size(self):
        if not self._recompute_size or not self.font:
            return
        if self.text:
            bbox = self.font.getbbox(self.text)
        else:
            # pick some value for empty lines
            bbox = self.font.bbox('T')
        self._size = (bbox[2], bbox[3])
        self._recompute_size = False

    def wrap(self, max_width):
        if self.width > max_width:
            average_char_size = math.ceil(self.width / len(self.text))
            max_char = max_width // average_char_size
            return (self.clone(self.text[:max_char]), self.clone(self.text[max_char:]))
        return (self, None)

class TypedLine():
    strings: list[TypedString]
    pos: tuple[int, int] = (0, 0)

    def __init__(self, strings=None):
        if not strings:
            strings = []
        self.strings = strings

    @property
    def width(self):
        return sum(string.width for string in self.strings)

    @property
    def height(self):
        return max(string.height for string in self.strings)

    def add_string(self, string):
        self.strings.append(string)

    def wrap(self, max_width):
        if self.width <= max_width:
            return [self]
        width = 0
        lines = []
        strings = list(self.strings)
        strings.reverse()
        line = TypedLine()
        while strings:
            string = strings.pop()
            width += string.width
            overdraw = width - max_width
            if overdraw:
                current_line_str, new_line_str = string.wrap(string.width - overdraw)
                line.add_string(current_line_str)
                lines.append(line)
                width = 0
                if new_line_str is not None:
                    if current_line_str:
                        raise ValueError(f"{new_line_str.text} cannot fit in {max_width}px")
                    strings.append(new_line_str)
                line = TypedLine()
            else:
                line.add_string(string)
        return lines

class TypedText():
    lines: list[TypedLine]

    def __init__(self):
        self.lines = []

    @staticmethod
    def from_typed_strings(typed_strings):
        """Create typed text from a list of typed strings, splitting lines on `\n`."""
        text = TypedText()
        typed_line = TypedLine()
        for typed_string in typed_strings:
            split_strings = typed_string.text.split('\n')
            typed_line.add_string(typed_string.clone(split_strings[0]))
            for split_string in split_strings[1:]:
                text.add_line(typed_line)
                typed_line = TypedLine([typed_string.clone(split_string)])
        if typed_line.strings:
            text.add_line(typed_line)
        return text

    @property
    def width(self):
        return max(line.width for line in self.lines)
    @property
    def height(self):
        return sum(line.height for line in self.lines)

    def add_line(self, line: TypedLine):
        self.lines.append(line)

    def get_fonts(self):
        return set(subline.font for line in self.lines for subline in line if subline.font)

    def wrap(self, max_width):
        if max_width == 0 or self.width <= max_width:
            return self
        text = TypedText()
        for line in self.lines:
            for new_line in line.wrap(max_width):
                text.add_line(new_line)
        return text

    def align(self, xy, align_method='left'):
        """Take in text and return a list of positions and text lines to draw the text aligned in some manner.

        :return TypedText: an instance of TypedText with lines positioned and sized appropriately.
        """
        (x, y), (x_size, _) = xy
        text = self.wrap(x_size)
        # the fonts should be fairly similar
        if align_method == 'left':
            current_y = y
            for line in text.lines:
                line.pos = (x, current_y)
                current_y += line.height
            return text
        if not x_size:
            raise ValueError(f'Text with no width bounds cannot be aligned to {align_method}')
        if align_method == 'center':
            current_y = y
            for line in text.lines:
                x_diff = (x_size - line.width) // 2
                line.pos = (x + x_diff, current_y)
                current_y += line.height
            return text
        raise ValueError(f'Invalid align method: {align_method}')

def get_rgb_from_hex(color_string):
    """:param str color_string: hex representation of rgb in hexadecimal"""
    color_string = color_string.lstrip("#")
    if not isinstance(color_string, str) or len(color_string) != 6:
        raise ValueError('Invalid color string', color_string)
    r, g, b = (int(color_string[start:start + 2], 16) for start in range(0, 6, 2))
    return (r, g, b)

def get_shape(shape='rect', color=(0, 0, 0, 255), ssscale=1, xy=(0, 0), sampler=Image.LANCZOS):
    """Get a shape sampled from a shape `ssscale` times bigger to avoid aliasing, if necessary.

    :param str shape: any of the valid image_crop selection value for <social.share.image.render.element>
    :param tuple[int; 3] | tuple[int; 4] color: 8-bit RGB color with or without alpha channel
    :param int ssscale: how much to scale the image before supersampling
    :param tuple[int, int]: size in x and y
    :param int Image: valid Image supersampling value from PIL
    """
    dimensions = (xy[0] * ssscale, xy[1] * ssscale) if shape != 'rect' else xy
    image = Image.new('RGBA', dimensions, (0, 0, 0, 0))
    editor = ImageDraw.ImageDraw(image)

    if shape == 'rect':
        editor.rectangle((0, 0, *dimensions), fill=color)
        return image
    if shape == 'circ':
        editor.ellipse((0, 0, *dimensions), fill=color)
    elif shape == 'roundrect':
        editor.rounded_rectangle((0, 0, *dimensions), fill=color, radius=dimensions[1])
    return image.resize(xy, sampler)

def fit_to_mask(image, shape, xy=None, shrink_fit=True):
    """Fit image to a mask of shape `crop_type` and dimensions `xy`.

    :param Image image: PIL image
    :param str shape: any of the valid image_crop selection value for <social.share.image.render.element>
    :param tuple[int, int] xy: size in x and y
    :param bool shrink_fit: shrink the image to fit inside the area before cropping, maintaining the original aspect ratio
    :return Image: PIL image of dimensions xy
    """
    if shrink_fit and xy and len(xy) == 2 and xy[0] and xy[1]:
        # find the most oversized axis and resize the other size based on ratio
        x_diff = image.size[0] - xy[0]
        y_diff = image.size[1] - xy[1]
        new_x, new_y = image.size
        if x_diff > 0 and x_diff > y_diff:
            x_shrink_ratio = image.size[0] / xy[0]
            new_x = xy[0]
            new_y = math.floor(image.size[1] / x_shrink_ratio)
        elif y_diff > 0:
            y_shrink_ratio = image.size[1] / xy[1]
            new_x = math.floor(image.size[0] / y_shrink_ratio)
            new_y = xy[1]
        image = image.resize((new_x, new_y))
    if not shape:
        return image
    else:
        if xy is not None and any(xy):
            # crop image to fit, if it wasn't resized
            x_size, y_size = xy
            ix_size, iy_size = image.size
            x_diff = ix_size - x_size
            y_diff = iy_size - y_size
            image = image.crop((
                max(x_diff, 0) / 2,
                max(y_diff, 0) / 2,
                ix_size - max(x_diff, 0) / 2,
                iy_size - max(y_diff, 0) / 2,
            ))
            # find diff if it doesn't fit exactly
            im_pos = (max(-x_diff, 0) // 2, max(-y_diff, 0) // 2)
        else:
            xy = image.size
            im_pos = (0, 0)
        if xy != image.size:
            undersized_image = image
            image = Image.new('RGBA', xy, (0, 0, 0, 0))
            image.paste(undersized_image, im_pos)
        shape = get_shape(shape=shape, ssscale=4, xy=xy)
        shape.paste(image, (0, 0), shape)
        return shape
