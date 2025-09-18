"""Image utilities.

Pure Python image helpers with no Odoo dependencies.
Uses PIL/Pillow for image processing.

Note: This module raises ValueError for invalid images. For Odoo-specific
usage with UserError, use odoo.tools.image instead.
"""

from .utils import (
    # Constants
    FILETYPE_BASE64_MAGICWORD,
    EXIF_TAG_ORIENTATION,
    IMAGE_MAX_RESOLUTION,
    # Classes
    ImageProcess,
    # Functions
    image_fix_orientation,
    image_apply_opt,
    image_to_base64,
    image_data_uri,
    image_process,
    average_dominant_color,
    binary_to_image,
    base64_to_image,
    get_webp_size,
    is_image_size_above,
    image_guess_size_from_field_name,
)

__all__ = [
    "EXIF_TAG_ORIENTATION",
    # Constants
    "FILETYPE_BASE64_MAGICWORD",
    "IMAGE_MAX_RESOLUTION",
    # Classes
    "ImageProcess",
    "average_dominant_color",
    "base64_to_image",
    "binary_to_image",
    "get_webp_size",
    "image_apply_opt",
    "image_data_uri",
    # Functions
    "image_fix_orientation",
    "image_guess_size_from_field_name",
    "image_process",
    "image_to_base64",
    "is_image_size_above",
]
