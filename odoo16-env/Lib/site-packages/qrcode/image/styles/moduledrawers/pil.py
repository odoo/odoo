from typing import TYPE_CHECKING, List

from PIL import Image, ImageDraw
from qrcode.image.styles.moduledrawers.base import QRModuleDrawer

if TYPE_CHECKING:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.main import ActiveWithNeighbors

# When drawing antialiased things, make them bigger and then shrink them down
# to size after the geometry has been drawn.
ANTIALIASING_FACTOR = 4


class StyledPilQRModuleDrawer(QRModuleDrawer):
    """
    A base class for StyledPilImage module drawers.

    NOTE: the color that this draws in should be whatever is equivalent to
    black in the color space, and the specified QRColorMask will handle adding
    colors as necessary to the image
    """

    img: "StyledPilImage"


class SquareModuleDrawer(StyledPilQRModuleDrawer):
    """
    Draws the modules as simple squares
    """

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.imgDraw = ImageDraw.Draw(self.img._img)

    def drawrect(self, box, is_active: bool):
        if is_active:
            self.imgDraw.rectangle(box, fill=self.img.paint_color)


class GappedSquareModuleDrawer(StyledPilQRModuleDrawer):
    """
    Draws the modules as simple squares that are not contiguous.

    The size_ratio determines how wide the squares are relative to the width of
    the space they are printed in
    """

    def __init__(self, size_ratio=0.8):
        self.size_ratio = size_ratio

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.imgDraw = ImageDraw.Draw(self.img._img)
        self.delta = (1 - self.size_ratio) * self.img.box_size / 2

    def drawrect(self, box, is_active: bool):
        if is_active:
            smaller_box = (
                box[0][0] + self.delta,
                box[0][1] + self.delta,
                box[1][0] - self.delta,
                box[1][1] - self.delta,
            )
            self.imgDraw.rectangle(smaller_box, fill=self.img.paint_color)


class CircleModuleDrawer(StyledPilQRModuleDrawer):
    """
    Draws the modules as circles
    """

    circle = None

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        box_size = self.img.box_size
        fake_size = box_size * ANTIALIASING_FACTOR
        self.circle = Image.new(
            self.img.mode,
            (fake_size, fake_size),
            self.img.color_mask.back_color,
        )
        ImageDraw.Draw(self.circle).ellipse(
            (0, 0, fake_size, fake_size), fill=self.img.paint_color
        )
        self.circle = self.circle.resize((box_size, box_size), Image.Resampling.LANCZOS)

    def drawrect(self, box, is_active: bool):
        if is_active:
            self.img._img.paste(self.circle, (box[0][0], box[0][1]))


class RoundedModuleDrawer(StyledPilQRModuleDrawer):
    """
    Draws the modules with all 90 degree corners replaced with rounded edges.

    radius_ratio determines the radius of the rounded edges - a value of 1
    means that an isolated module will be drawn as a circle, while a value of 0
    means that the radius of the rounded edge will be 0 (and thus back to 90
    degrees again).
    """

    needs_neighbors = True

    def __init__(self, radius_ratio=1):
        self.radius_ratio = radius_ratio

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.corner_width = int(self.img.box_size / 2)
        self.setup_corners()

    def setup_corners(self):
        mode = self.img.mode
        back_color = self.img.color_mask.back_color
        front_color = self.img.paint_color
        self.SQUARE = Image.new(
            mode, (self.corner_width, self.corner_width), front_color
        )

        fake_width = self.corner_width * ANTIALIASING_FACTOR
        radius = self.radius_ratio * fake_width
        diameter = radius * 2
        base = Image.new(
            mode, (fake_width, fake_width), back_color
        )  # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0, 0, diameter, diameter), fill=front_color)
        base_draw.rectangle((radius, 0, fake_width, fake_width), fill=front_color)
        base_draw.rectangle((0, radius, fake_width, fake_width), fill=front_color)
        self.NW_ROUND = base.resize(
            (self.corner_width, self.corner_width), Image.Resampling.LANCZOS
        )
        self.SW_ROUND = self.NW_ROUND.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        self.SE_ROUND = self.NW_ROUND.transpose(Image.Transpose.ROTATE_180)
        self.NE_ROUND = self.NW_ROUND.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    def drawrect(self, box: List[List[int]], is_active: "ActiveWithNeighbors"):
        if not is_active:
            return
        # find rounded edges
        nw_rounded = not is_active.W and not is_active.N
        ne_rounded = not is_active.N and not is_active.E
        se_rounded = not is_active.E and not is_active.S
        sw_rounded = not is_active.S and not is_active.W

        nw = self.NW_ROUND if nw_rounded else self.SQUARE
        ne = self.NE_ROUND if ne_rounded else self.SQUARE
        se = self.SE_ROUND if se_rounded else self.SQUARE
        sw = self.SW_ROUND if sw_rounded else self.SQUARE
        self.img._img.paste(nw, (box[0][0], box[0][1]))
        self.img._img.paste(ne, (box[0][0] + self.corner_width, box[0][1]))
        self.img._img.paste(
            se, (box[0][0] + self.corner_width, box[0][1] + self.corner_width)
        )
        self.img._img.paste(sw, (box[0][0], box[0][1] + self.corner_width))


class VerticalBarsDrawer(StyledPilQRModuleDrawer):
    """
    Draws vertically contiguous groups of modules as long rounded rectangles,
    with gaps between neighboring bands (the size of these gaps is inversely
    proportional to the horizontal_shrink).
    """

    needs_neighbors = True

    def __init__(self, horizontal_shrink=0.8):
        self.horizontal_shrink = horizontal_shrink

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.half_height = int(self.img.box_size / 2)
        self.delta = int((1 - self.horizontal_shrink) * self.half_height)
        self.setup_edges()

    def setup_edges(self):
        mode = self.img.mode
        back_color = self.img.color_mask.back_color
        front_color = self.img.paint_color

        height = self.half_height
        width = height * 2
        shrunken_width = int(width * self.horizontal_shrink)
        self.SQUARE = Image.new(mode, (shrunken_width, height), front_color)

        fake_width = width * ANTIALIASING_FACTOR
        fake_height = height * ANTIALIASING_FACTOR
        base = Image.new(
            mode, (fake_width, fake_height), back_color
        )  # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0, 0, fake_width, fake_height * 2), fill=front_color)

        self.ROUND_TOP = base.resize((shrunken_width, height), Image.Resampling.LANCZOS)
        self.ROUND_BOTTOM = self.ROUND_TOP.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    def drawrect(self, box, is_active: "ActiveWithNeighbors"):
        if is_active:
            # find rounded edges
            top_rounded = not is_active.N
            bottom_rounded = not is_active.S

            top = self.ROUND_TOP if top_rounded else self.SQUARE
            bottom = self.ROUND_BOTTOM if bottom_rounded else self.SQUARE
            self.img._img.paste(top, (box[0][0] + self.delta, box[0][1]))
            self.img._img.paste(
                bottom, (box[0][0] + self.delta, box[0][1] + self.half_height)
            )


class HorizontalBarsDrawer(StyledPilQRModuleDrawer):
    """
    Draws horizontally contiguous groups of modules as long rounded rectangles,
    with gaps between neighboring bands (the size of these gaps is inversely
    proportional to the vertical_shrink).
    """

    needs_neighbors = True

    def __init__(self, vertical_shrink=0.8):
        self.vertical_shrink = vertical_shrink

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.half_width = int(self.img.box_size / 2)
        self.delta = int((1 - self.vertical_shrink) * self.half_width)
        self.setup_edges()

    def setup_edges(self):
        mode = self.img.mode
        back_color = self.img.color_mask.back_color
        front_color = self.img.paint_color

        width = self.half_width
        height = width * 2
        shrunken_height = int(height * self.vertical_shrink)
        self.SQUARE = Image.new(mode, (width, shrunken_height), front_color)

        fake_width = width * ANTIALIASING_FACTOR
        fake_height = height * ANTIALIASING_FACTOR
        base = Image.new(
            mode, (fake_width, fake_height), back_color
        )  # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0, 0, fake_width * 2, fake_height), fill=front_color)

        self.ROUND_LEFT = base.resize(
            (width, shrunken_height), Image.Resampling.LANCZOS
        )
        self.ROUND_RIGHT = self.ROUND_LEFT.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    def drawrect(self, box, is_active: "ActiveWithNeighbors"):
        if is_active:
            # find rounded edges
            left_rounded = not is_active.W
            right_rounded = not is_active.E

            left = self.ROUND_LEFT if left_rounded else self.SQUARE
            right = self.ROUND_RIGHT if right_rounded else self.SQUARE
            self.img._img.paste(left, (box[0][0], box[0][1] + self.delta))
            self.img._img.paste(
                right, (box[0][0] + self.half_width, box[0][1] + self.delta)
            )
