# Needed on case-insensitive filesystems
from __future__ import absolute_import

# Try to import PIL in either of the two ways it can be installed.
try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    import Image
    import ImageDraw

# When drawing antialiased things, make them bigger and then shrink them down to size after the geometry has been drawn
ANTIALIASING_FACTOR = 4

class QRModuleDrawer:
    """
    QRModuleDrawer exists to draw the modules of the  QR Code onto a PIL image
    For this, technically all that is necessary is a drawrect_context(self, box, is_active, context) function
    which takes in the box in which it is to draw, whether or not the box is "active" (a module exists there),
    and the context (the neighboring pixels)
    It is frequently necessary to also implement an "initialize" function to set up values that only the containing StyledPilImage
    knows about.
    NOTE: the color that this draws in should be whatever is equivalent to black in the color space, and the specified QRColorMask
    will handle adding colors as necessary to the image

    For examples of what these look like, see doc/module_drawers.png
    """

    fill = None
    def initialize(self, styledPilImage, image):
        self.fill = styledPilImage.paint_color

    def drawrect_context(self, box, is_active, context):
        raise NotImplementedError("QRModuleDrawer.drawrect_context")

    # helper for figuring out the context, which is an array containing information on neighboring pixels
    # I refer to these by their cardinal directions, like:
    # [NW, N,  NE,
    #  W,      E,
    #  SW, S,  SE]
    DIRECTIONS = {
        'NW': 0,
        'N': 1,
        'NE': 2,
        'W': 3,
        'E': 4,
        'SW': 5,
        'S': 6,
        'SE': 7
    }
    def get(self, context, direction):
        return context[self.DIRECTIONS[direction]]

class SquareModuleDrawer(QRModuleDrawer):
    """
    Draws the modules as simple squares
    """
    fill = None
    def initialize(self, styledPilImage, image):
        self.imgDraw = ImageDraw.Draw(image)
        self.fill = styledPilImage.paint_color
    def drawrect_context(self, box, is_active, context):
        if is_active:
            self.imgDraw.rectangle(box, fill=self.fill)

class GappedSquareModuleDrawer(QRModuleDrawer):
    """
    Draws the modules as simple squares that are not contiguous.
    The size_ratio determines how wide the squares are relative to the width of the space they are printed in
    """
    fill = None
    def __init__(self, size_ratio = 0.8):
        self.size_ratio = size_ratio
    def initialize(self, styledPilImage, image):
        self.imgDraw = ImageDraw.Draw(image)
        self.fill = styledPilImage.paint_color
        self.delta = (1 - self.size_ratio) * styledPilImage.box_size / 2
    def drawrect_context(self, box, is_active, context):
        if is_active:
            smaller_box = (
                box[0][0] + self.delta,
                box[0][1] + self.delta,
                box[1][0] - self.delta,
                box[1][1] - self.delta
            )
            self.imgDraw.rectangle(smaller_box, fill=self.fill)

class CircleModuleDrawer(QRModuleDrawer):
    """
    Draws the modules as circles
    """
    circle = None
    def initialize(self, styledPilImage, image):
        box_size = styledPilImage.box_size
        fake_size = box_size * ANTIALIASING_FACTOR
        self.circle = Image.new(styledPilImage.mode,(fake_size, fake_size), styledPilImage.color_mask.back_color)
        ImageDraw.Draw(self.circle).ellipse((0,0, fake_size, fake_size), fill = styledPilImage.paint_color)
        self.circle = self.circle.resize((box_size, box_size), Image.LANCZOS)
        self.image = image
    def drawrect_context(self, box, is_active, context):
        if is_active:
            self.image.paste(self.circle, (box[0][0], box[0][1]))

class RoundedModuleDrawer(QRModuleDrawer):
    """
    Draws the modules with all 90 degree corners replaced with rounded edges
    radius_ratio determines the radius of the rounded edges -
    a value of 1 means that an isolated module will be drawn as a circle,
    while a value of 0 means that the radius of the rounded edge will be 0 (and thus back to 90 degrees again)
    """
    def __init__(self, radius_ratio = 1):
        self.radius_ratio = radius_ratio

    def initialize(self, styledPilImage, image):
        self.corner_width = int(styledPilImage.box_size / 2)
        self.image = image
        self.setup_corners(styledPilImage.mode, styledPilImage.color_mask.back_color, styledPilImage.paint_color)
    def setup_corners(self, mode, back_color, front_color):
        self.SQUARE = Image.new(mode, (self.corner_width, self.corner_width), front_color)

        fake_width = self.corner_width * ANTIALIASING_FACTOR
        radius = self.radius_ratio * fake_width
        diameter = radius * 2
        base = Image.new(mode, (fake_width, fake_width), back_color) # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0,0, diameter, diameter), fill = front_color)
        base_draw.rectangle((radius, 0, fake_width, fake_width), fill = front_color)
        base_draw.rectangle((0, radius, fake_width, fake_width), fill = front_color)
        self.NW_ROUND = base.resize((self.corner_width, self.corner_width), Image.LANCZOS)
        self.SW_ROUND = self.NW_ROUND.transpose(Image.FLIP_TOP_BOTTOM)
        self.SE_ROUND = self.NW_ROUND.transpose(Image.ROTATE_180)
        self.NE_ROUND = self.NW_ROUND.transpose(Image.FLIP_LEFT_RIGHT)

    def drawrect_context(self, box, is_active, context):
        if not is_active:
            return
        # find rounded edges
        nw_rounded = not self.get(context, 'W') and not self.get(context, 'N')
        ne_rounded = not self.get(context, 'N') and not self.get(context, 'E')
        se_rounded = not self.get(context, 'E') and not self.get(context, 'S')
        sw_rounded = not self.get(context, 'S') and not self.get(context, 'W')

        nw = self.NW_ROUND if nw_rounded else self.SQUARE
        ne = self.NE_ROUND if ne_rounded else self.SQUARE
        se = self.SE_ROUND if se_rounded else self.SQUARE
        sw = self.SW_ROUND if sw_rounded else self.SQUARE
        self.image.paste(nw, (box[0][0], box[0][1]))
        self.image.paste(ne, (box[0][0] + self.corner_width, box[0][1]))
        self.image.paste(se, (box[0][0] + self.corner_width, box[0][1] + self.corner_width))
        self.image.paste(sw, (box[0][0], box[0][1] + self.corner_width))


class VerticalBarsDrawer(QRModuleDrawer):
    """
    Draws vertically contiguous groups of modules as long rounded rectangles, with gaps between neighboring bands
    (the size of these gaps is inversely proportional to the horizontal_shrink)
    """
    def __init__(self, horizontal_shrink = 0.8):
        self.horizontal_shrink = horizontal_shrink

    def initialize(self, styledPilImage, image):
        self.half_height = int(styledPilImage.box_size / 2)
        self.image = image
        self.delta = int((1-self.horizontal_shrink) * self.half_height)
        self.setup_edges(styledPilImage.mode, styledPilImage.color_mask.back_color, styledPilImage.paint_color)

    def setup_edges(self, mode, back_color, front_color):
        height = self.half_height
        width = height * 2
        shrunken_width = int(width * self.horizontal_shrink)
        self.SQUARE = Image.new(mode, (shrunken_width, height), front_color)

        fake_width = width * ANTIALIASING_FACTOR
        fake_height = height * ANTIALIASING_FACTOR
        radius = fake_width
        base = Image.new(mode, (fake_width, fake_height), back_color) # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0,0, fake_width, fake_height * 2), fill = front_color)

        self.ROUND_TOP = base.resize((shrunken_width, height), Image.LANCZOS)
        self.ROUND_BOTTOM = self.ROUND_TOP.transpose(Image.FLIP_TOP_BOTTOM)

    def drawrect_context(self, box, is_active, context):
        if is_active:
            # find rounded edges
            top_rounded = not self.get(context, 'N')
            bottom_rounded = not self.get(context, 'S')

            top = self.ROUND_TOP if top_rounded else self.SQUARE
            bottom = self.ROUND_BOTTOM if bottom_rounded else self.SQUARE
            self.image.paste(top, (box[0][0] + self.delta, box[0][1]))
            self.image.paste(bottom, (box[0][0] + self.delta, box[0][1] + self.half_height))

class HorizontalBarsDrawer(QRModuleDrawer):
    """
    Draws horizontally contiguous groups of modules as long rounded rectangles, with gaps between neighboring bands
    (the size of these gaps is inversely proportional to the vertical_shrink)
    """
    def __init__(self, vertical_shrink = 0.8):
        self.vertical_shrink = vertical_shrink

    def initialize(self, styledPilImage, image):
        self.half_width = int(styledPilImage.box_size / 2)
        self.image = image
        self.delta = int((1-self.vertical_shrink) * self.half_width)
        self.setup_edges(styledPilImage.mode, styledPilImage.color_mask.back_color, styledPilImage.paint_color)

    def setup_edges(self, mode, back_color, front_color):
        width = self.half_width
        height = width * 2
        shrunken_height= int(height * self.vertical_shrink)
        self.SQUARE = Image.new(mode, (width, shrunken_height), front_color)

        fake_width = width * ANTIALIASING_FACTOR
        fake_height = height * ANTIALIASING_FACTOR
        radius = fake_height
        base = Image.new(mode, (fake_width, fake_height), back_color) # make something 4x bigger for antialiasing
        base_draw = ImageDraw.Draw(base)
        base_draw.ellipse((0,0, fake_width * 2, fake_height), fill = front_color)

        self.ROUND_LEFT = base.resize((width, shrunken_height), Image.LANCZOS)
        self.ROUND_RIGHT = self.ROUND_LEFT.transpose(Image.FLIP_LEFT_RIGHT)

    def drawrect_context(self, box, is_active, context):
        if is_active:
            # find rounded edges
            left_rounded = not self.get(context, 'W')
            right_rounded = not self.get(context, 'E')

            left = self.ROUND_LEFT if left_rounded else self.SQUARE
            right = self.ROUND_RIGHT if right_rounded else self.SQUARE
            self.image.paste(left, (box[0][0], box[0][1] + self.delta))
            self.image.paste(right, (box[0][0] + self.half_width, box[0][1] + self.delta))
