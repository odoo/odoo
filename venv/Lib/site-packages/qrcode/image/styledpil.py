# Needed on case-insensitive filesystems
from __future__ import absolute_import

import qrcode.image.base
from qrcode.compat.pil import Image
from qrcode.image.styles.colormasks import QRColorMask, SolidFillColorMask
from qrcode.image.styles.moduledrawers import SquareModuleDrawer


class StyledPilImage(qrcode.image.base.BaseImageWithDrawer):
    """
    Styled PIL image builder, default format is PNG.

    This differs from the PilImage in that there is a module_drawer, a
    color_mask, and an optional image

    The module_drawer should extend the QRModuleDrawer class and implement the
    drawrect_context(self, box, active, context), and probably also the
    initialize function. This will draw an individual "module" or square on
    the QR code.

    The color_mask will extend the QRColorMask class and will at very least
    implement the get_fg_pixel(image, x, y) function, calculating a color to
    put on the image at the pixel location (x,y) (more advanced functionality
    can be gotten by instead overriding other functions defined in the
    QRColorMask class)

    The Image can be specified either by path or with a Pillow Image, and if it
    is there will be placed in the middle of the QR code. No effort is done to
    ensure that the QR code is still legible after the image has been placed
    there; Q or H level error correction levels are recommended to maintain
    data integrity A resampling filter can be specified (defaulting to
    PIL.Image.Resampling.LANCZOS) for resizing; see PIL.Image.resize() for possible
    options for this parameter.
    """

    kind = "PNG"

    needs_processing = True
    color_mask: QRColorMask
    default_drawer_class = SquareModuleDrawer

    def __init__(self, *args, **kwargs):
        self.color_mask = kwargs.get("color_mask", SolidFillColorMask())
        embeded_image_path = kwargs.get("embeded_image_path", None)
        self.embeded_image = kwargs.get("embeded_image", None)
        self.embeded_image_resample = kwargs.get(
            "embeded_image_resample", Image.Resampling.LANCZOS
        )
        if not self.embeded_image and embeded_image_path:
            self.embeded_image = Image.open(embeded_image_path)

        # the paint_color is the color the module drawer will use to draw upon
        # a canvas During the color mask process, pixels that are paint_color
        # are replaced by a newly-calculated color
        self.paint_color = tuple(0 for i in self.color_mask.back_color)
        if self.color_mask.has_transparency:
            self.paint_color = tuple([*self.color_mask.back_color[:3], 255])

        super().__init__(*args, **kwargs)

    def new_image(self, **kwargs):
        mode = (
            "RGBA"
            if (
                self.color_mask.has_transparency
                or (self.embeded_image and "A" in self.embeded_image.getbands())
            )
            else "RGB"
        )
        # This is the background color. Should be white or whiteish
        back_color = self.color_mask.back_color

        return Image.new(mode, (self.pixel_size, self.pixel_size), back_color)

    def init_new_image(self):
        self.color_mask.initialize(self, self._img)
        super().init_new_image()

    def process(self):
        self.color_mask.apply_mask(self._img)
        if self.embeded_image:
            self.draw_embeded_image()

    def draw_embeded_image(self):
        if not self.embeded_image:
            return
        total_width, _ = self._img.size
        total_width = int(total_width)
        logo_width_ish = int(total_width / 4)
        logo_offset = (
            int((int(total_width / 2) - int(logo_width_ish / 2)) / self.box_size)
            * self.box_size
        )  # round the offset to the nearest module
        logo_position = (logo_offset, logo_offset)
        logo_width = total_width - logo_offset * 2
        region = self.embeded_image
        region = region.resize((logo_width, logo_width), self.embeded_image_resample)
        if "A" in region.getbands():
            self._img.alpha_composite(region, logo_position)
        else:
            self._img.paste(region, logo_position)

    def save(self, stream, format=None, **kwargs):
        if format is None:
            format = kwargs.get("kind", self.kind)
        if "kind" in kwargs:
            del kwargs["kind"]
        self._img.save(stream, format=format, **kwargs)

    def __getattr__(self, name):
        return getattr(self._img, name)
