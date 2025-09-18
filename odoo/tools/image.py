# ruff: noqa: F401
"""
Odoo image processing utilities.

This module wraps odoo.libs.image to provide Odoo-specific error handling
(UserError instead of ValueError) for better user experience.

For agnostic usage without Odoo dependencies, use odoo.libs.image directly.
"""

from PIL import Image

from odoo.exceptions import UserError
from odoo.libs.colors import (
    get_lightness,
    get_saturation,
    hex_to_rgb,
    rgb_to_hex,
)

# Re-export everything from libs/image (agnostic versions)
from odoo.libs.image import (
    EXIF_TAG_ORIENTATION,
    # Constants
    FILETYPE_BASE64_MAGICWORD,
    IMAGE_MAX_RESOLUTION,
    average_dominant_color,
    image_apply_opt,
    image_data_uri,
    # Functions that don't need wrapping
    image_fix_orientation,
    image_guess_size_from_field_name,
    image_to_base64,
)

# Import the agnostic versions for wrapping
from odoo.libs.image import (
    ImageProcess as _ImageProcessBase,
)
from odoo.libs.image import (
    base64_to_image as _base64_to_image_base,
)
from odoo.libs.image import (
    binary_to_image as _binary_to_image_base,
)
from odoo.libs.image import (
    get_webp_size as _get_webp_size_base,
)
from odoo.libs.image import (
    image_process as _image_process_base,
)
from odoo.libs.image import (
    is_image_size_above as _is_image_size_above_base,
)
from odoo.tools.translate import LazyTranslate

__all__ = ["image_process"]
_lt = LazyTranslate("base")


class ImageProcess(_ImageProcessBase):
    """Odoo-specific ImageProcess that raises UserError instead of ValueError.

    This provides better user experience in Odoo by showing translated
    error messages to users.
    """

    def __init__(self, source, verify_resolution=True):
        """Initialize the ``source`` image for processing.

        :param bytes source: the original image binary
        :param verify_resolution: if True, verify the image resolution is acceptable
        :raise: UserError if the image can't be decoded or is too large
        """
        try:
            super().__init__(source, verify_resolution)
        except ValueError as e:
            # Convert ValueError to UserError with translated message
            error_msg = str(e)
            if "could not be decoded" in error_msg:
                raise UserError(_lt("This file could not be decoded as an image file."))
            if "Too large image" in error_msg:
                raise UserError(
                    _lt(
                        "Too large image (above %sMpx), reduce the image size.",
                        str(IMAGE_MAX_RESOLUTION / 1e6),
                    )
                )
            raise UserError(error_msg)  # pylint: disable=E8502


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
    """Process the `source` image by executing the given operations.

    Wrapper around libs.image.image_process that uses UserError.
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


def binary_to_image(source):
    """Convert binary data to a PIL Image.

    :param source: binary image data
    :return: PIL Image object
    :raise: UserError if the source can't be decoded as an image
    """
    try:
        return _binary_to_image_base(source)
    except ValueError:
        raise UserError(_lt("This file could not be decoded as an image file."))


def base64_to_image(base64_source: str | bytes) -> Image:
    """Return a PIL image from the given `base64_source`.

    :param base64_source: the image base64 encoded
    :return: PIL Image object
    :raise: UserError if the base64 is incorrect or the image can't be identified by PIL
    """
    try:
        return _base64_to_image_base(base64_source)
    except ValueError:
        raise UserError(_lt("This file could not be decoded as an image file."))


def get_webp_size(source):
    """
    Returns the size of the provided webp binary source.

    :param source: binary source
    :return: (width, height) tuple, or None if not supported
    :raise: UserError if source is not a webp file
    """
    try:
        return _get_webp_size_base(source)
    except ValueError:
        raise UserError(_lt("This file is not a webp file."))


def is_image_size_above(base64_source_1, base64_source_2):
    """Return whether or not the size of the given image `base64_source_1` is
    above the size of the given image `base64_source_2`.

    This version uses UserError for invalid images.
    """
    try:
        return _is_image_size_above_base(base64_source_1, base64_source_2)
    except ValueError:
        raise UserError(_lt("This file could not be decoded as an image file."))
