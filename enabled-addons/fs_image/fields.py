# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=method-required-super
from contextlib import contextmanager
from io import BytesIO, IOBase

from odoo.exceptions import UserError
from odoo.tools.image import image_process

from odoo.addons.fs_attachment.models.ir_attachment import IrAttachment
from odoo.addons.fs_file.fields import FSFile, FSFileValue


class FSImageValue(FSFileValue):
    """Value for the FSImage field"""

    def __init__(
        self,
        attachment: IrAttachment = None,
        name: str = None,
        value: bytes | IOBase = None,
        alt_text: str = None,
    ) -> None:
        super().__init__(attachment, name, value)
        if self._attachment and alt_text is not None:
            raise ValueError(
                "FSImageValue cannot be initialized with an attachment and an"
                " alt_text at the same time. When initializing with an attachment,"
                " you can't pass any other argument."
            )
        self._alt_text = alt_text

    @property
    def alt_text(self) -> str:
        alt_text = self._attachment.alt_text if self._attachment else self._alt_text
        return alt_text

    @alt_text.setter
    def alt_text(self, value: str) -> None:
        if self._attachment:
            self._attachment.alt_text = value
        else:
            self._alt_text = value

    @classmethod
    def from_fs_file_value(cls, fs_file_value: FSFileValue) -> "FSImageValue":
        if isinstance(fs_file_value, FSImageValue):
            return fs_file_value
        return cls(
            attachment=fs_file_value.attachment,
            name=fs_file_value.name if not fs_file_value.attachment else None,
            value=fs_file_value._buffer
            if not fs_file_value.attachment
            else fs_file_value._buffer,
        )

    def image_process(
        self,
        size=(0, 0),
        verify_resolution=False,
        quality=0,
        crop=None,
        colorize=False,
        output_format="",
    ):
        """
        Process the image to adapt it to the given parameters.
        :param size: a tuple (max_width, max_height) containing the maximum
            width and height of the processed image.
            If one of the value is 0, it will be calculated to keep the aspect
            ratio.
            If both values are 0, the image will not be resized.
        :param verify_resolution: if True, make sure the original image size is not
            excessive before starting to process it. The max allowed resolution is
            defined by `IMAGE_MAX_RESOLUTION` in :class:`odoo.tools.image.ImageProcess`.
        :param int quality: quality setting to apply. Default to 0.

            - for JPEG: 1 is worse, 95 is best. Values above 95 should be
              avoided. Falsy values will fallback to 95, but only if the image
              was changed, otherwise the original image is returned.
            - for PNG: set falsy to prevent conversion to a WEB palette.
            - for other formats: no effect.
        :param crop: (True | 'top' | 'bottom'):
            * True, the image will be cropped to the given size.
            * 'top', the image will be cropped at the top to the given size.
            * 'bottom', the image will be cropped at the bottom to the given size.
            Otherwise, it will be resized to fit the given size.
        :param colorize: if True, the transparent background of the image
            will be colorized in a random color.
        :param str output_format: the output format. Can be PNG, JPEG, GIF, or ICO.
            Default to the format of the original image. BMP is converted to
            PNG, other formats than those mentioned above are converted to JPEG.
        :return: the processed image as bytes
        """
        return image_process(
            self.getvalue(),
            size=size,
            crop=crop,
            quality=quality,
            verify_resolution=verify_resolution,
            colorize=colorize,
            output_format=output_format,
        )


class FSImage(FSFile):
    """
    This field is a FSFile field with an alt_text attribute used to encapsulate
    an image file stored in a filesystem storage.

    It's inspired by the 'image' field of odoo :class:`odoo.fields.Binary` but
    is designed to store the image in a filesystem storage instead of the
    database.

    If image size is greater than the ``max_width``/``max_height`` limit of pixels,
    the image will be resized to the limit by keeping aspect ratio.

    :param int max_width: the maximum width of the image (default: ``0``, no limit)
    :param int max_height: the maximum height of the image (default: ``0``, no limit)
    :param bool verify_resolution: whether the image resolution should be verified
        to ensure it doesn't go over the maximum image resolution
        (default: ``True``).
        See :class:`odoo.tools.image.ImageProcess` for maximum image resolution
        (default: ``50e6``).
    """

    type = "fs_image"

    max_width = 0
    max_height = 0
    verify_resolution = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_process_mode = False

    def create(self, record_values):
        with self._set_image_process_mode():
            return super().create(record_values)

    def write(self, records, value):
        if isinstance(value, dict) and "content" not in value:
            # we are writing on the alt_text field only
            return self._update_alt_text(records, value)
        with self._set_image_process_mode():
            return super().write(records, value)

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return None
        if isinstance(value, FSImageValue):
            cache_value = value
        else:
            cache_value = super().convert_to_cache(value, record, validate)
        if not isinstance(cache_value, FSImageValue):
            cache_value = FSImageValue.from_fs_file_value(cache_value)
        if isinstance(value, dict) and "alt_text" in value:
            cache_value.alt_text = value["alt_text"]
        if self._image_process_mode and cache_value.is_new:
            name = cache_value.name
            new_value = BytesIO(self._image_process(cache_value))
            cache_value._buffer = new_value
            cache_value.name = name
        return cache_value

    def _create_attachment(self, record, cache_value):
        attachment = super()._create_attachment(record, cache_value)
        # odoo filter out additional fields in create method on ir.attachment
        # so we need to write the alt_text after the creation
        if cache_value.alt_text:
            attachment.alt_text = cache_value.alt_text
        return attachment

    def _convert_attachment_to_cache(self, attachment: IrAttachment) -> FSImageValue:
        cache_value = super()._convert_attachment_to_cache(attachment)
        return FSImageValue.from_fs_file_value(cache_value)

    def _image_process(self, cache_value: FSImageValue) -> bytes | None:
        if self.readonly and not self.max_width and not self.max_height:
            # no need to process images for computed fields, or related fields
            return cache_value.getvalue()
        return (
            cache_value.image_process(
                size=(self.max_width, self.max_height),
                verify_resolution=self.verify_resolution,
            )
            or None
        )

    def convert_to_read(self, value, record, use_name_get=True) -> dict | None:
        vals = super().convert_to_read(value, record, use_name_get)
        if isinstance(value, FSImageValue):
            vals["alt_text"] = value.alt_text or None
        return vals

    @contextmanager
    def _set_image_process_mode(self):
        self._image_process_mode = True
        try:
            yield
        finally:
            self._image_process_mode = False

    def _process_related(self, value: FSImageValue, env):
        """Override to resize the related value before saving it on self."""
        if not value:
            return None
        if self.readonly and not self.max_width and not self.max_height:
            # no need to process images for computed fields, or related fields
            # without max_width/max_height
            return value
        value = super()._process_related(value, env)
        new_value = BytesIO(self._image_process(value))
        return FSImageValue(value=new_value, alt_text=value.alt_text, name=value.name)

    def _update_alt_text(self, records, value: dict):
        for record in records:
            if not record[self.name]:
                raise UserError(
                    record.env._(
                        "Cannot set alt_text on empty image "
                        "(record %(record)s.%(field_name)s)",
                        record=record,
                        field_name=self.name,
                    )
                )
            record[self.name].alt_text = value["alt_text"]
        return True
