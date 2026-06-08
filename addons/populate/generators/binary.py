from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image as PilImage

from odoo.tools.binary import BinaryBytes

from .generator import Generator

if TYPE_CHECKING:
    from odoo.api import ValuesType


class Binary(Generator):
    """
    Generate random binary content as a ``BinaryBytes`` value.

    Produces pseudo-random bytes of a configurable ``size``. Suitable for
    any ``binary`` field that does not require a specific file format.

    :param int size: Number of random bytes to generate (default: ``1024``).
    """
    name = 'binary.binary'
    allowed_field_types = ('binary', 'virtual')

    def __init__(self, size: int = 1024, **kwargs):
        super().__init__(**kwargs)
        if size <= 0:
            raise ValueError(self.env._("Size must be a positive integer, got %(size)s.", size=size))
        self.size = size

    def _next(self, known_vals: ValuesType) -> BinaryBytes | bool:
        return BinaryBytes(self.random.randbytes(self.size))

    @classmethod
    def convert_to_kwargs(cls, attrs: dict) -> dict:
        kwargs = super().convert_to_kwargs(attrs)
        if 'size' in attrs:
            kwargs['size'] = int(attrs['size'])
        return kwargs


class Image(Generator):
    """
    Generate a minimal valid flat-colored JPEG image as a ``BinaryBytes`` value.

    :param int width: Image width in pixels (default: ``64``).
    :param int height: Image height in pixels (default: ``64``).
    """
    name = 'binary.image'
    allowed_field_types = ('binary', 'virtual')  # `image` fields have type='binary' in the ORM

    def __init__(self, width: int = 64, height: int = 64, **kwargs):
        super().__init__(**kwargs)
        if width <= 0 or height <= 0:
            raise ValueError(self.env._(
                "Image dimensions must be positive integers, got %(width)sx%(height)s.",
                width=width, height=height,
            ))
        self.width = width
        self.height = height

    def _next(self, known_vals: ValuesType) -> BinaryBytes | bool:
        color = (
            self.distribution.sample_discrete(0, 255),
            self.distribution.sample_discrete(0, 255),
            self.distribution.sample_discrete(0, 255),
        )
        buf = io.BytesIO()
        PilImage.new('RGB', (self.width, self.height), color).save(buf, format='JPEG')
        return BinaryBytes(buf.getvalue())

    @classmethod
    def convert_to_kwargs(cls, attrs: dict) -> dict:
        kwargs = super().convert_to_kwargs(attrs)
        for key in ('width', 'height'):
            if key in attrs:
                kwargs[key] = int(attrs[key])
        return kwargs
