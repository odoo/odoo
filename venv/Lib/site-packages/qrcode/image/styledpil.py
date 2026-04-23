# Needed on case-insensitive filesystems
from __future__ import absolute_import

# Try to import PIL in either of the two ways it can be installed.
try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    import Image
    import ImageDraw

import qrcode.image.base

from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import SquareModuleDrawer
class StyledPilImage(qrcode.image.base.BaseImage):
    """
    Styled PIL image builder, default format is PNG.
    This differs from the PilImage in that there is a module_drawer, a color_mask, and an optional image

    The module_drawer should extend the QRModuleDrawer class and implement the
    drawrect_context(self, box, active, context), and probably also the intitialize
    function. This will draw an individual "module" or square on the QR code.

    The color_mask will extend the QRColorMask class and will at very least implement the
    get_fg_pixel(image, x, y) function, calculating a color to put on the image at the pixel location (x,y)
    (more advanced functionality can be gotten by instead overriding other functions defined in the QRColorMask class)


    The Image can be specified either by path or with a Pillow Image, and if it is there will be placed in the
    middle of the QR code. No effort is done to ensure that the QR code is still legible after the image has been
    placed there; Q or H level error correction levels are recommended to maintain data integrity
    A resampling filter can be specified (defaulting to PIL.Image.LANCZOS) for resizing; see PIL.Image.resize() for
    possible options for this parameter.
    """
    kind = "PNG"

    needs_context = True
    needs_processing = True

    def new_image(self, **kwargs):
        self.color_mask = kwargs.get("color_mask", SolidFillColorMask())
        self.module_drawer = kwargs.get("module_drawer", SquareModuleDrawer())
        # The eye drawer can be overridden by another module drawer as well, but you have to be more careful with these in order to
        # make the QR code still parseable
        self.eye_drawer = kwargs.get("eye_drawer", SquareModuleDrawer())

        embeded_image_path = kwargs.get("embeded_image_path", None)
        self.embeded_image = kwargs.get("embeded_image", None)
        self.embeded_image_resample = kwargs.get("embeded_image_resample", Image.LANCZOS)
        if not self.embeded_image and embeded_image_path:
            self.embeded_image = Image.open(embeded_image_path)
        mode = "RGBA" if (self.color_mask.has_transparency or (self.embeded_image and 'A' in self.embeded_image.getbands())) else "RGB"
        self.mode = mode

        self.back_color = self.color_mask.back_color # This is the background color. Should be white or whiteish

        img = Image.new(mode, (self.pixel_size, self.pixel_size), self.back_color)

        # the paint_color is the color the module drawer will use to draw upon a canvas
        # During the color mask process, pixels that are paint_color are replaced by a newly-calculated color
        self.paint_color = tuple(0 for i in self.color_mask.back_color)
        if self.color_mask.has_transparency:
            self.paint_color = tuple([*self.color_mask.back_color[:3], 255])

        self.color_mask.initialize(self, img)
        self.module_drawer.initialize(self, img)
        self.eye_drawer.initialize(self, img)
        return img

    def drawrect_context(self, row, col, is_active, context):
        box = self.pixel_box(row, col)
        if self.is_eye(row, col):
            self.eye_drawer.drawrect_context(box, is_active, context)
        else:
            self.module_drawer.drawrect_context(box, is_active, context)

    def process(self):
        self.color_mask.apply_mask(self._img)
        if self.embeded_image:
            self.draw_embeded_image()

    def draw_embeded_image(self):
            total_width,_ = self._img.size
            total_width = int(total_width)
            logo_width_ish = int(total_width / 4)
            logo_offset = int( (int(total_width / 2) - int(logo_width_ish / 2)) / self.box_size) * self.box_size # round the offset to the nearest module
            logo_position = (logo_offset, logo_offset)
            logo_width = total_width - logo_offset*2
            region = self.embeded_image
            region = region.resize((logo_width, logo_width), self.embeded_image_resample)
            if 'A' in region.getbands():
                self._img.alpha_composite(region, logo_position)
            else:
                self._img.paste(region, logo_position)

    # The eyes are treated differently, and this will find whether the referenced module is in an eye
    def is_eye(self, row, col):
        return (
            (row < 7 and col < 7)
            or (row < 7 and self.width - col < 8)
            or (self.width - row < 8 and col < 7)
        )

    def save(self, stream, format=None, **kwargs):
        if format is None:
            format = kwargs.get("kind", self.kind)
        if "kind" in kwargs:
            del kwargs["kind"]
        self._img.save(stream, format=format, **kwargs)

    def __getattr__(self, name):
        return getattr(self._img, name)
