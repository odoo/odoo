# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from abc import abstractmethod
from io import BytesIO
from os import path
from PIL import Image

from odoo.modules import get_module_path

from .image_render_utils import get_shape, fit_to_mask, get_rgb_from_hex
from .renderer import FieldRenderer, Renderer
from .renderer_text import UserTextRenderer

class ShapeRenderer(Renderer):
    def __init__(self, *args, shape='rect', **kwargs):
        self.shape = shape
        super().__init__(self, *args, shape=shape, **kwargs)

class ImageShapeRenderer(ShapeRenderer):
    use_placeholder: bool

    def __init__(self, *args, use_placeholder=False, **kwargs):
        super().__init__(*args, use_placeholder=use_placeholder, **kwargs)
        self.use_placeholder = use_placeholder

    @abstractmethod
    def get_image(self, *args, **kwargs):
        return None

    def render_image(self, *args, record=None, **kwargs):
        image = self.get_image(self, *args, record=record, **kwargs)
        if image:
            image = Image.open(BytesIO(base64.b64decode(image))).convert('RGBA')
        elif self.use_placeholder:
            image = Image.open(path.join(get_module_path('web'), 'static', 'img', 'placeholder.png'))
        else:
            return None
        image = fit_to_mask(image, self.shape, xy=self.size)
        if any(self.size) and image.size != self.size:
            image = image.crop((0, 0, *self.size))
        return image

class ImageFieldShapeRenderer(ImageShapeRenderer, FieldRenderer):

    def __init__(self, *args, use_placeholder=True, **kwargs):
        super().__init__(*args, use_placeholder=use_placeholder, **kwargs)

    def get_image(self, *args, record=None, **kwargs):
        return self.get_field_value(record=record)

    def render_image(self, *args, record=None, **kwargs):
        return super().render_image(*args, record=record, **kwargs)

class ImageStaticShapeRenderer(ImageShapeRenderer):
    def __init__(self, *args, image='', **kwargs):
        self.image = image or ''
        super().__init__(self, *args, image=image, **kwargs)

    def get_image(self, *args, **kwargs):
        return self.image

class ColorShapeRenderer(ShapeRenderer):
    color: tuple[int, int, int]

    def __init__(self, *args, color: str = '000000', **kwargs):
        self.color = get_rgb_from_hex(color or '000000')
        super().__init__(self, *args, color=color, **kwargs)

    def render_image(self, *args, **kwargs):
        if not self.shape:
            return None
        return get_shape(self.shape or 'rect', self.color, 4, self.size)
