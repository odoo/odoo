"""Image utilities.

Pure Python image helpers with no Odoo dependencies.
Uses PIL/Pillow for image processing.
"""

import base64
import binascii
import io
from random import randrange

# We can preload Ico too because it is considered safe
from PIL import (
    IcoImagePlugin,  # noqa: F401
    Image,
    ImageOps,
)
from PIL.Image import Image as PILImage
from PIL.Image import Palette, Resampling

# Maps only the 6 first bits of the base64 data, accurate enough
# for our purpose and faster than decoding the full blob first
FILETYPE_BASE64_MAGICWORD = {
    b"/": "jpg",
    b"R": "gif",
    b"i": "png",
    b"P": "svg+xml",
    b"U": "webp",
}

# EXIF orientation tag (kept for backward compatibility)
EXIF_TAG_ORIENTATION = 0x112

# Arbitrary limit to fit most resolutions, including Samsung Galaxy A22 photo,
# 8K with a ratio up to 16:10, and almost all variants of 4320p
IMAGE_MAX_RESOLUTION = 50e6

# Preload PIL with the minimal subset of image formats we need
Image.preinit()
Image._initialized = 2


def image_fix_orientation(image: PILImage) -> PILImage:
    """Fix the orientation of the image if it has an EXIF orientation tag.

    Delegates to Pillow's ``ImageOps.exif_transpose()`` which handles all
    8 EXIF orientation values and clears the tag after transposing.

    :param image: the source image
    :return: the resulting image with orientation fixed
    """
    return ImageOps.exif_transpose(image)


def image_apply_opt(image: PILImage, output_format: str, **params) -> bytes:
    """Return the serialization of the provided `image` to `output_format` using `params`.

    :param image: the image to encode
    :param output_format: PIL Image.save() format parameter (e.g., 'JPEG', 'PNG')
    :param params: params to expand when calling Image.save()
    :return: the image formatted as bytes
    """
    if output_format == "JPEG" and image.mode not in ["1", "L", "RGB"]:
        image = image.convert("RGB")
    stream = io.BytesIO()
    image.save(stream, format=output_format, **params)
    return stream.getvalue()


def image_to_base64(image: PILImage, output_format: str, **params) -> bytes:
    """Return a base64-encoded image from the given PIL `image`.

    :param image: the PIL Image object
    :param output_format: PIL Image.save() format parameter (e.g., 'JPEG', 'PNG')
    :param params: params to expand when calling Image.save()
    :return: the image base64 encoded
    """
    stream = image_apply_opt(image, output_format, **params)
    return base64.b64encode(stream)


def image_data_uri(base64_source: bytes) -> str:
    """Return a data URL scheme according to RFC 2397.

    See: https://tools.ietf.org/html/rfc2397

    Supports PNG, GIF, JPG and SVG images, defaulting to PNG type
    if no mimetype is detected.

    :param base64_source: base64 encoded image data
    :return: data URI string

    Example::

        >>> image_data_uri(b'iVBORw0KGgo=')
        'data:image/png;base64,iVBORw0KGgo='
    """
    filetype = FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], "png")
    return f"data:image/{filetype};base64,{base64_source.decode()}"


class ImageProcess:
    """Process images with various operations like resize, crop, colorize.

    This is an agnostic version that raises ValueError for invalid images.
    For Odoo-specific usage with UserError, use odoo.tools.image.ImageProcess.
    """

    def __init__(self, source, verify_resolution=True):
        """Initialize the ``source`` image for processing.

        :param bytes source: the original image binary

            No processing will be done if the `source` is falsy or if
            the image is SVG.
        :param verify_resolution: if True, make sure the original image size is not
            excessive before starting to process it. The max allowed resolution is
            defined by `IMAGE_MAX_RESOLUTION`.
        :type verify_resolution: bool
        :rtype: ImageProcess

        :raise: ValueError if `verify_resolution` is True and the image is too large
        :raise: ValueError if the image can't be identified by PIL
        """
        self.source = source or False
        self.operationsCount = 0

        if (
            not source
            or source[:1] == b"<"
            or (source[0:4] == b"RIFF" and source[8:15] == b"WEBPVP8")
        ):
            # don't process empty source or SVG or WEBP
            self.image = False
        else:
            try:
                self.image = Image.open(io.BytesIO(source))
            except OSError, binascii.Error:
                raise ValueError("This file could not be decoded as an image file.")

            # Original format has to be saved before fixing the orientation or
            # doing any other operations because the information will be lost on
            # the resulting image.
            self.original_format = (self.image.format or "").upper()

            self.image = image_fix_orientation(self.image)

            w, h = self.image.size
            if verify_resolution and w * h > IMAGE_MAX_RESOLUTION:
                raise ValueError(
                    f"Too large image (above {IMAGE_MAX_RESOLUTION / 1e6}Mpx), reduce the image size."
                )

    def image_quality(self, quality=0, output_format=""):
        """Return the image resulting of all the image processing
        operations that have been applied previously.

        The source is returned as-is if it's an SVG, or if no operations have
        been applied, the `output_format` is the same as the original format,
        and the quality is not specified.

        :param int quality: quality setting to apply. Default to 0.

            - for JPEG: 1 is worse, 95 is best. Values above 95 should be
              avoided. Falsy values will fallback to 95, but only if the image
              was changed, otherwise the original image is returned.
            - for PNG: set falsy to prevent conversion to a WEB palette.
            - for other formats: no effect.

        :param str output_format: Can be PNG, JPEG, GIF, or ICO.
            Default to the format of the original image if a valid output format,
            otherwise BMP is converted to PNG and the rest are converted to JPEG.
        :return: the final image, or ``False`` if the original ``source`` was falsy.
        :rtype: bytes | False
        """
        if not self.image:
            return self.source

        output_image = self.image

        output_format = output_format.upper() or self.original_format
        if output_format == "BMP":
            output_format = "PNG"
        elif output_format not in ["PNG", "JPEG", "GIF", "ICO"]:
            output_format = "JPEG"

        if (
            not self.operationsCount
            and output_format == self.original_format
            and not quality
        ):
            return self.source

        opt = {"output_format": output_format}

        if output_format == "PNG":
            opt["optimize"] = True
            if quality:
                if output_image.mode != "P":
                    # Floyd Steinberg dithering by default
                    output_image = output_image.convert("RGBA").convert(
                        "P", palette=Palette.WEB, colors=256
                    )
        if output_format == "JPEG":
            opt["optimize"] = True
            opt["quality"] = quality or 95
        if output_format == "GIF":
            opt["optimize"] = True
            opt["save_all"] = True

        if output_image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (
            output_format == "JPEG" and output_image.mode == "RGBA"
        ):
            output_image = output_image.convert("RGB")

        output_bytes = image_apply_opt(output_image, **opt)
        if (
            len(output_bytes) >= len(self.source)
            and self.original_format == output_format
            and not self.operationsCount
        ):
            # Format has not changed and image content is unchanged but the
            # reached binary is bigger: rather use the original.
            return self.source
        return output_bytes

    def resize(self, max_width=0, max_height=0, expand=False):
        """Resize the image.

        The image is not resized above the current image size, unless the expand
        parameter is True. This method is used by default to create smaller versions
        of the image.

        The current ratio is preserved. To change the ratio, see `crop_resize`.

        If `max_width` or `max_height` is falsy, it will be computed from the
        other to keep the current ratio. If both are falsy, no resize is done.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param int max_width: max width
        :param int max_height: max height
        :param bool expand: whether or not the image size can be increased
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.original_format != "GIF" and (max_width or max_height):
            w, h = self.image.size
            asked_width = max_width or (w * max_height) // h
            asked_height = max_height or (h * max_width) // w
            if expand and (asked_width > w or asked_height > h):
                self.image = self.image.resize((asked_width, asked_height))
                self.operationsCount += 1
                return self
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
        if self.image and self.original_format != "GIF" and max_width and max_height:
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

            # Dimensions should be at least 1.
            new_w, new_h = max(new_w, 1), max(new_h, 1)

            # Correctly place the center of the crop.
            x_offset = int((w - new_w) * center_x)
            h_offset = int((h - new_h) * center_y)

            if new_w != w or new_h != h:
                self.image = self.image.crop(
                    (x_offset, h_offset, x_offset + new_w, h_offset + new_h)
                )
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1

        return self.resize(max_width, max_height)

    def colorize(self, color=None):
        """Replace the transparent background by a given color, or by a random one.

        :param tuple color: RGB values for the color to use
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if color is None:
            color = (
                randrange(32, 224, 24),
                randrange(32, 224, 24),
                randrange(32, 224, 24),
            )
        if self.image:
            original = self.image
            self.image = Image.new("RGB", original.size)
            self.image.paste(color, box=(0, 0) + original.size)
            self.image.paste(original, mask=original)
            self.operationsCount += 1
        return self

    def add_padding(self, padding):
        """Expand the image size by adding padding around the image.

        :param int padding: thickness of the padding
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image:
            img_width, img_height = self.image.size
            self.image = self.image.resize(
                (img_width - 2 * padding, img_height - 2 * padding)
            )
            self.image = ImageOps.expand(self.image, border=padding)
            self.operationsCount += 1
        return self


def image_process(
    source,
    size=(0, 0),
    verify_resolution=False,
    quality=0,
    expand=False,
    crop=None,
    colorize=False,
    output_format="",
    padding=False,
):
    """Process the `source` image by executing the given operations and
    return the result image.
    """
    if not source or (
        (not size or (not size[0] and not size[1]))
        and not verify_resolution
        and not quality
        and not crop
        and not colorize
        and not output_format
        and not padding
    ):
        # for performance: don't do anything if the image is falsy or if
        # no operations have been requested
        return source

    image = ImageProcess(source, verify_resolution)
    if size:
        if crop:
            center_x = 0.5
            center_y = 0.5
            if crop == "top":
                center_y = 0
            elif crop == "bottom":
                center_y = 1
            image.crop_resize(
                max_width=size[0],
                max_height=size[1],
                center_x=center_x,
                center_y=center_y,
            )
        else:
            image.resize(max_width=size[0], max_height=size[1], expand=expand)
    if padding:
        image.add_padding(padding)
    if colorize:
        image.colorize(colorize if isinstance(colorize, tuple) else None)
    return image.image_quality(quality=quality, output_format=output_format)


# ----------------------------------------
# Misc image tools
# ---------------------------------------


def average_dominant_color(colors, mitigate=175, max_margin=140):
    """This function is used to calculate the dominant colors when given a list of colors.

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

    margins = [
        max_margin * (1 - dominant_color[0] / sum(col[0] for col in colors))
    ] * 3

    colors = [c for c in colors if c is not dominant_color]

    for color in colors:
        rgb = color[1]
        if (
            rgb[0] < dominant_rgb[0] + margins[0]
            and rgb[0] > dominant_rgb[0] - margins[0]
            and rgb[1] < dominant_rgb[1] + margins[1]
            and rgb[1] > dominant_rgb[1] - margins[1]
            and rgb[2] < dominant_rgb[2] + margins[2]
            and rgb[2] > dominant_rgb[2] - margins[2]
        ):
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
        value = (
            dominant_avg[color] / (brightest / mitigate)
            if brightest > mitigate
            else dominant_avg[color]
        )
        final_dominant.append(int(value))

    return tuple(final_dominant), remaining


def binary_to_image(source):
    """Convert binary data to a PIL Image.

    :param source: binary image data
    :return: PIL Image object
    :raise: ValueError if the source can't be decoded as an image
    """
    try:
        return Image.open(io.BytesIO(source))
    except OSError, binascii.Error:
        raise ValueError("This file could not be decoded as an image file.")


def base64_to_image(base64_source: str | bytes) -> Image:
    """Return a PIL image from the given `base64_source`.

    :param base64_source: the image base64 encoded
    :return: PIL Image object
    :raise: ValueError if the base64 is incorrect or the image can't be identified by PIL
    """
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_source)))
    except OSError, binascii.Error:
        raise ValueError("This file could not be decoded as an image file.")


def get_webp_size(source):
    """Returns the size of the provided webp binary source for VP8, VP8X and
    VP8L, otherwise returns None.
    See https://developers.google.com/speed/webp/docs/riff_container.

    :param source: binary source
    :return: (width, height) tuple, or None if not supported
    :raise: ValueError if source is not a webp file
    """
    if not (source[0:4] == b"RIFF" and source[8:15] == b"WEBPVP8"):
        raise ValueError("This file is not a webp file.")

    vp8_type = source[15]
    if vp8_type == 0x20:  # 0x20 = ' '
        # Sizes on big-endian 16 bits at offset 26.
        width_low, width_high, height_low, height_high = source[26:30]
        width = (width_high << 8) + width_low
        height = (height_high << 8) + height_low
        return (width, height)
    elif vp8_type == 0x58:  # 0x58 = 'X'
        # Sizes (minus one) on big-endian 24 bits at offset 24.
        (
            width_low,
            width_medium,
            width_high,
            height_low,
            height_medium,
            height_high,
        ) = source[24:30]
        width = 1 + (width_high << 16) + (width_medium << 8) + width_low
        height = 1 + (height_high << 16) + (height_medium << 8) + height_low
        return (width, height)
    elif vp8_type == 0x4C and source[20] == 0x2F:  # 0x4C = 'L'
        # Sizes (minus one) on big-endian-ish 14 bits at offset 21.
        # E.g. [@20] 2F ab cd ef gh
        # - width = 1 + (c&0x3)d ab: ignore the two high bits of the second byte
        # - height= 1 + hef(c&0xC>>2): used them as the first two bits of the height
        ab, cd, ef, gh = source[21:25]
        width = 1 + ((cd & 0x3F) << 8) + ab
        height = 1 + ((gh & 0xF) << 10) + (ef << 2) + (cd >> 6)
        return (width, height)
    return None


def is_image_size_above(base64_source_1, base64_source_2):
    """Return whether or not the size of the given image `base64_source_1` is
    above the size of the given image `base64_source_2`.
    """
    if not base64_source_1 or not base64_source_2:
        return False
    if base64_source_1[:1] in (b"P", "P") or base64_source_2[:1] in (b"P", "P"):
        # False for SVG
        return False

    class _SimpleSize:
        """Simple object with width/height attributes."""

        def __init__(self, width, height):
            self.width = width
            self.height = height

    def get_image_size(base64_source):
        source = base64.b64decode(base64_source)
        if source[0:4] == b"RIFF" and source[8:15] == b"WEBPVP8":
            size = get_webp_size(source)
            if size:
                return _SimpleSize(size[0], size[1])
            else:
                # False for unknown WEBP format
                return False
        else:
            return image_fix_orientation(binary_to_image(source))

    image_source = get_image_size(base64_source_1)
    image_target = get_image_size(base64_source_2)
    if not image_source or not image_target:
        return False
    return (
        image_source.width > image_target.width
        or image_source.height > image_target.height
    )


def image_guess_size_from_field_name(field_name: str) -> tuple[int, int]:
    """Attempt to guess the image size based on `field_name`.

    If it can't be guessed or if it is a custom field: return (0, 0) instead.

    :param field_name: the name of a field
    :return: the guessed size
    """
    if field_name == "image":
        return (1024, 1024)
    if field_name.startswith("x_"):
        return (0, 0)
    try:
        suffix = int(field_name.rsplit("_", 1)[-1])
    except ValueError:
        return 0, 0

    if suffix < 16:
        # If the suffix is less than 16, it's probably not the size
        return (0, 0)

    return (suffix, suffix)
