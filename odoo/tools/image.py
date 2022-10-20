# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
import io

from PIL import Image, ImageOps
# We can preload Ico too because it is considered safe
from PIL import IcoImagePlugin
try:
    from PIL.Image import Transpose, Palette, Resampling
except ImportError:
    Transpose = Palette = Resampling = Image

from random import randrange

from odoo.exceptions import UserError
from odoo.tools.translate import _


# Preload PIL with the minimal subset of image formats we need
Image.preinit()
Image._initialized = 2

# Maps only the 6 first bits of the base64 data, accurate enough
# for our purpose and faster than decoding the full blob first
FILETYPE_BASE64_MAGICWORD = {
    b'/': 'jpg',
    b'R': 'gif',
    b'i': 'png',
    b'P': 'svg+xml',
}

EXIF_TAG_ORIENTATION = 0x112
# The target is to have 1st row/col to be top/left
# Note: rotate is counterclockwise
EXIF_TAG_ORIENTATION_TO_TRANSPOSE_METHODS = { # Initial side on 1st row/col:
    0: [],                                              # reserved
    1: [],                                              # top/left
    2: [Transpose.FLIP_LEFT_RIGHT],                     # top/right
    3: [Transpose.ROTATE_180],                          # bottom/right
    4: [Transpose.FLIP_TOP_BOTTOM],                     # bottom/left
    5: [Transpose.FLIP_LEFT_RIGHT, Transpose.ROTATE_90],# left/top
    6: [Transpose.ROTATE_270],                          # right/top
    7: [Transpose.FLIP_TOP_BOTTOM, Transpose.ROTATE_90],# right/bottom
    8: [Transpose.ROTATE_90],                           # left/bottom
}

# Arbitrary limit to fit most resolutions, including Samsung Galaxy A22 photo,
# 8K with a ratio up to 16:10, and almost all variants of 4320p
IMAGE_MAX_RESOLUTION = 50e6


class ImageProcess():

    def __init__(self, source, verify_resolution=True):
        """Initialize the `source` image for processing.

        :param source: the original image binary

            No processing will be done if the `source` is falsy or if
            the image is SVG.

        :param verify_resolution: if True, make sure the original image size is not
            excessive before starting to process it. The max allowed resolution is
            defined by `IMAGE_MAX_RESOLUTION`.
        :type verify_resolution: bool
        :rtype: ImageProcess

        :raise: ValueError if `verify_resolution` is True and the image is too large
        :raise: UserError if the image can't be identified by PIL
        """
        self.source = source or False
        self.operationsCount = 0

        if not source or source[:1] == b'<':
            # don't process empty source or SVG
            self.image = False
        else:
            try:
                self.image = Image.open(io.BytesIO(source))
            except (OSError, binascii.Error):
                raise UserError(_("This file could not be decoded as an image file."))

            # Original format has to be saved before fixing the orientation or
            # doing any other operations because the information will be lost on
            # the resulting image.
            self.original_format = (self.image.format or '').upper()

            self.image = image_fix_orientation(self.image)

            w, h = self.image.size
            if verify_resolution and w * h > IMAGE_MAX_RESOLUTION:
                raise ValueError(_("Image size excessive, uploaded images must be smaller than %s million pixels.", str(IMAGE_MAX_RESOLUTION / 1e6)))

    def image_quality(self, quality=0, output_format=''):
        """Return the image resulting of all the image processing
        operations that have been applied previously.

        Return False if the initialized `image` was falsy, and return
        the initialized `image` without change if it was SVG.

        Also return the initialized `image` if no operations have been applied
        and the `output_format` is the same as the original format and the
        quality is not specified.

        :param int quality: quality setting to apply. Default to 0.

            - for JPEG: 1 is worse, 95 is best. Values above 95 should be
              avoided. Falsy values will fallback to 95, but only if the image
              was changed, otherwise the original image is returned.
            - for PNG: set falsy to prevent conversion to a WEB palette.
            - for other formats: no effect.
        :param str output_format: the output format. Can be PNG, JPEG, GIF, or ICO.
            Default to the format of the original image. BMP is converted to
            PNG, other formats than those mentioned above are converted to JPEG.
        :return: image
        :rtype: bytes or False
        """
        if not self.image:
            return self.source

        output_image = self.image

        output_format = output_format.upper() or self.original_format
        if output_format == 'BMP':
            output_format = 'PNG'
        elif output_format not in ['PNG', 'JPEG', 'GIF', 'ICO']:
            output_format = 'JPEG'

        if not self.operationsCount and output_format == self.original_format and not quality:
            return self.source

        opt = {'output_format': output_format}

        if output_format == 'PNG':
            opt['optimize'] = True
            if quality:
                if output_image.mode != 'P':
                    # Floyd Steinberg dithering by default
                    output_image = output_image.convert('RGBA').convert('P', palette=Palette.WEB, colors=256)
        if output_format == 'JPEG':
            opt['optimize'] = True
            opt['quality'] = quality or 95
        if output_format == 'GIF':
            opt['optimize'] = True
            opt['save_all'] = True

        if output_image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (output_format == 'JPEG' and output_image.mode == 'RGBA'):
            output_image = output_image.convert("RGB")

        return image_apply_opt(output_image, **opt)

    def resize(self, max_width=0, max_height=0):
        """Resize the image.

        The image is never resized above the current image size. This method is
        only to create a smaller version of the image.

        The current ratio is preserved. To change the ratio, see `crop_resize`.

        If `max_width` or `max_height` is falsy, it will be computed from the
        other to keep the current ratio. If both are falsy, no resize is done.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param int max_width: max width
        :param int max_height: max height
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.original_format != 'GIF' and (max_width or max_height):
            w, h = self.image.size
            asked_width = max_width or (w * max_height) // h
            asked_height = max_height or (h * max_width) // w
            if asked_width != w or asked_height != h:
                self.image.thumbnail((asked_width, asked_height), Resampling.LANCZOS)
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1
        return self

    def crop_resize(self, max_width, max_height, center_x=0.5, center_y=0.5):
        """Crop and resize the image.

        The image is never resized above the current image size. This method is
        only to create smaller versions of the image.

        Instead of preserving the ratio of the original image like `resize`,
        this method will force the output to take the ratio of the given
        `max_width` and `max_height`, so both have to be defined.

        The crop is done before the resize in order to preserve as much of the
        original image as possible. The goal of this method is primarily to
        resize to a given ratio, and it is not to crop unwanted parts of the
        original image. If the latter is what you want to do, you should create
        another method, or directly use the `crop` method from PIL.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param int max_width: max width
        :param int max_height: max height
        :param float center_x: the center of the crop between 0 (left) and 1
            (right). Defaults to 0.5 (center).
        :param float center_y: the center of the crop between 0 (top) and 1
            (bottom). Defaults to 0.5 (center).
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.original_format != 'GIF' and max_width and max_height:
            w, h = self.image.size
            # We want to keep as much of the image as possible -> at least one
            # of the 2 crop dimensions always has to be the same value as the
            # original image.
            # The target size will be reached with the final resize.
            if w / max_width > h / max_height:
                new_w, new_h = w, (max_height * w) // max_width
            else:
                new_w, new_h = (max_width * h) // max_height, h

            # No cropping above image size.
            if new_w > w:
                new_w, new_h = w, (new_h * w) // new_w
            if new_h > h:
                new_w, new_h = (new_w * h) // new_h, h

            # Correctly place the center of the crop.
            x_offset = int((w - new_w) * center_x)
            h_offset = int((h - new_h) * center_y)

            if new_w != w or new_h != h:
                self.image = self.image.crop((x_offset, h_offset, x_offset + new_w, h_offset + new_h))
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1

        return self.resize(max_width, max_height)

    def colorize(self):
        """Replace the transparent background by a random color.

        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image:
            original = self.image
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            self.image = Image.new('RGB', original.size)
            self.image.paste(color, box=(0, 0) + original.size)
            self.image.paste(original, mask=original)
            self.operationsCount += 1
        return self


def image_process(source, size=(0, 0), verify_resolution=False, quality=0, crop=None, colorize=False, output_format=''):
    """Process the `source` image by executing the given operations and
    return the result image.
    """
    if not source or ((not size or (not size[0] and not size[1])) and not verify_resolution and not quality and not crop and not colorize and not output_format):
        # for performance: don't do anything if the image is falsy or if
        # no operations have been requested
        return source

    image = ImageProcess(source, verify_resolution)
    if size:
        if crop:
            center_x = 0.5
            center_y = 0.5
            if crop == 'top':
                center_y = 0
            elif crop == 'bottom':
                center_y = 1
            image.crop_resize(max_width=size[0], max_height=size[1], center_x=center_x, center_y=center_y)
        else:
            image.resize(max_width=size[0], max_height=size[1])
    if colorize:
        image.colorize()
    return image.image_quality(quality=quality, output_format=output_format)


# ----------------------------------------
# Misc image tools
# ---------------------------------------

def average_dominant_color(colors, mitigate=175, max_margin=140):
    """This function is used to calculate the dominant colors when given a list of colors

    There are 5 steps:

    1) Select dominant colors (highest count), isolate its values and remove
       it from the current color set.
    2) Set margins according to the prevalence of the dominant color.
    3) Evaluate the colors. Similar colors are grouped in the dominant set
       while others are put in the "remaining" list.
    4) Calculate the average color for the dominant set. This is done by
       averaging each band and joining them into a tuple.
    5) Mitigate final average and convert it to hex

    :param colors: list of tuples having:

        0. color count in the image
        1. actual color: tuple(R, G, B, A)

        -> these can be extracted from a PIL image using
        :meth:`~PIL.Image.Image.getcolors`
    :param mitigate: maximum value a band can reach
    :param max_margin: maximum difference from one of the dominant values
    :returns: a tuple with two items:

        0. the average color of the dominant set as: tuple(R, G, B)
        1. list of remaining colors, used to evaluate subsequent dominant colors
    """
    dominant_color = max(colors)
    dominant_rgb = dominant_color[1][:3]
    dominant_set = [dominant_color]
    remaining = []

    margins = [max_margin * (1 - dominant_color[0] /
                             sum([col[0] for col in colors]))] * 3

    colors.remove(dominant_color)

    for color in colors:
        rgb = color[1]
        if (rgb[0] < dominant_rgb[0] + margins[0] and rgb[0] > dominant_rgb[0] - margins[0] and
            rgb[1] < dominant_rgb[1] + margins[1] and rgb[1] > dominant_rgb[1] - margins[1] and
                rgb[2] < dominant_rgb[2] + margins[2] and rgb[2] > dominant_rgb[2] - margins[2]):
            dominant_set.append(color)
        else:
            remaining.append(color)

    dominant_avg = []
    for band in range(3):
        avg = total = 0
        for color in dominant_set:
            avg += color[0] * color[1][band]
            total += color[0]
        dominant_avg.append(int(avg / total))

    final_dominant = []
    brightest = max(dominant_avg)
    for color in range(3):
        value = dominant_avg[color] / (brightest / mitigate) if brightest > mitigate else dominant_avg[color]
        final_dominant.append(int(value))

    return tuple(final_dominant), remaining


def image_fix_orientation(image):
    """Fix the orientation of the image if it has an EXIF orientation tag.

    This typically happens for images taken from a non-standard orientation
    by some phones or other devices that are able to report orientation.

    The specified transposition is applied to the image before all other
    operations, because all of them expect the image to be in its final
    orientation, which is the case only when the first row of pixels is the top
    of the image and the first column of pixels is the left of the image.

    Moreover the EXIF tags will not be kept when the image is later saved, so
    the transposition has to be done to ensure the final image is correctly
    orientated.

    Note: to be completely correct, the resulting image should have its exif
    orientation tag removed, since the transpositions have been applied.
    However since this tag is not used in the code, it is acceptable to
    save the complexity of removing it.

    :param image: the source image
    :type image: ~PIL.Image.Image
    :return: the resulting image, copy of the source, with orientation fixed
        or the source image if no operation was applied
    :rtype: ~PIL.Image.Image
    """
    getexif = getattr(image, 'getexif', None) or getattr(image, '_getexif', None)  # support PIL < 6.0
    if getexif:
        exif = getexif()
        if exif:
            orientation = exif.get(EXIF_TAG_ORIENTATION, 0)
            for method in EXIF_TAG_ORIENTATION_TO_TRANSPOSE_METHODS.get(orientation, []):
                image = image.transpose(method)
            return image
    return image


def binary_to_image(source):
    try:
        return Image.open(io.BytesIO(source))
    except (OSError, binascii.Error):
        raise UserError(_("This file could not be decoded as an image file."))

def base64_to_image(base64_source):
    """Return a PIL image from the given `base64_source`.

    :param base64_source: the image base64 encoded
    :type base64_source: string or bytes
    :rtype: ~PIL.Image.Image
    :raise: UserError if the base64 is incorrect or the image can't be identified by PIL
    """
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_source)))
    except (OSError, binascii.Error):
        raise UserError(_("This file could not be decoded as an image file."))


def image_apply_opt(image, output_format, **params):
    """Return the given PIL `image` using `params`.

    :type image: ~PIL.Image.Image
    :param str output_format: :meth:`~PIL.Image.Image.save`'s ``format`` parameter
    :param dict params: params to expand when calling :meth:`~PIL.Image.Image.save`
    :return: the image formatted
    :rtype: bytes
    """
    stream = io.BytesIO()
    image.save(stream, format=output_format, **params)
    return stream.getvalue()


def image_to_base64(image, output_format, **params):
    """Return a base64_image from the given PIL `image` using `params`.

    :type image: ~PIL.Image.Image
    :param str output_format:
    :param dict params: params to expand when calling :meth:`~PIL.Image.Image.save`
    :return: the image base64 encoded
    :rtype: bytes
    """
    stream = image_apply_opt(image, output_format, **params)
    return base64.b64encode(stream)


def is_image_size_above(base64_source_1, base64_source_2):
    """Return whether or not the size of the given image `base64_source_1` is
    above the size of the given image `base64_source_2`.
    """
    if not base64_source_1 or not base64_source_2:
        return False
    if base64_source_1[:1] in (b'P', 'P') or base64_source_2[:1] in (b'P', 'P'):
        # False for SVG
        return False
    image_source = image_fix_orientation(base64_to_image(base64_source_1))
    image_target = image_fix_orientation(base64_to_image(base64_source_2))
    return image_source.width > image_target.width or image_source.height > image_target.height


def image_guess_size_from_field_name(field_name):
    """Attempt to guess the image size based on `field_name`.

    If it can't be guessed, return (0, 0) instead.

    :param str field_name: the name of a field
    :return: the guessed size
    :rtype: tuple (width, height)
    """
    suffix = '1024' if field_name == 'image' else field_name.split('_')[-1]
    try:
        return (int(suffix), int(suffix))
    except ValueError:
        return (0, 0)


def image_data_uri(base64_source):
    """This returns data URL scheme according RFC 2397
    (https://tools.ietf.org/html/rfc2397) for all kind of supported images
    (PNG, GIF, JPG and SVG), defaulting on PNG type if not mimetype detected.
    """
    return 'data:image/%s;base64,%s' % (
        FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], 'png'),
        base64_source.decode(),
    )


def get_saturation(rgb):
    """Returns the saturation (hsl format) of a given rgb color

    :param rgb: rgb tuple or list
    :return: saturation
    """
    c_max = max(rgb) / 255
    c_min = min(rgb) / 255
    d = c_max - c_min
    return 0 if d == 0 else d / (1 - abs(c_max + c_min - 1))


def get_lightness(rgb):
    """Returns the lightness (hsl format) of a given rgb color

    :param rgb: rgb tuple or list
    :return: lightness
    """
    return (max(rgb) + min(rgb)) / 2 / 255


def hex_to_rgb(hx):
    """Converts an hexadecimal string (starting with '#') to a RGB tuple"""
    return tuple([int(hx[i:i+2], 16) for i in range(1, 6, 2)])


def rgb_to_hex(rgb):
    """Converts a RGB tuple or list to an hexadecimal string"""
    return '#' + ''.join([(hex(c).split('x')[-1].zfill(2)) for c in rgb])
