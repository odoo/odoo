import qrcode.image.base
from qrcode.compat.pil import Image, ImageDraw


class PilImage(qrcode.image.base.BaseImage):
    """
    PIL image builder, default format is PNG.
    """

    kind = "PNG"

    def new_image(self, **kwargs):
        back_color = kwargs.get("back_color", "white")
        fill_color = kwargs.get("fill_color", "black")

        try:
            fill_color = fill_color.lower()
        except AttributeError:
            pass

        try:
            back_color = back_color.lower()
        except AttributeError:
            pass

        # L mode (1 mode) color = (r*299 + g*587 + b*114)//1000
        if fill_color == "black" and back_color == "white":
            mode = "1"
            fill_color = 0
            if back_color == "white":
                back_color = 255
        elif back_color == "transparent":
            mode = "RGBA"
            back_color = None
        else:
            mode = "RGB"

        img = Image.new(mode, (self.pixel_size, self.pixel_size), back_color)
        self.fill_color = fill_color
        self._idr = ImageDraw.Draw(img)
        return img

    def drawrect(self, row, col):
        box = self.pixel_box(row, col)
        self._idr.rectangle(box, fill=self.fill_color)

    def save(self, stream, format=None, **kwargs):
        kind = kwargs.pop("kind", self.kind)
        if format is None:
            format = kind
        self._img.save(stream, format=format, **kwargs)

    def __getattr__(self, name):
        return getattr(self._img, name)
