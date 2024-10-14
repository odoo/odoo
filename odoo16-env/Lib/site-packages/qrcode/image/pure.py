from itertools import chain

from qrcode.compat.png import PngWriter
from qrcode.image.base import BaseImage


class PyPNGImage(BaseImage):
    """
    pyPNG image builder.
    """

    kind = "PNG"
    allowed_kinds = ("PNG",)
    needs_drawrect = False

    def new_image(self, **kwargs):
        if not PngWriter:
            raise ImportError("PyPNG library not installed.")

        return PngWriter(self.pixel_size, self.pixel_size, greyscale=True, bitdepth=1)

    def drawrect(self, row, col):
        """
        Not used.
        """

    def save(self, stream, kind=None):
        if isinstance(stream, str):
            stream = open(stream, "wb")
        self._img.write(stream, self.rows_iter())

    def rows_iter(self):
        yield from self.border_rows_iter()
        border_col = [1] * (self.box_size * self.border)
        for module_row in self.modules:
            row = (
                border_col
                + list(
                    chain.from_iterable(
                        ([not point] * self.box_size) for point in module_row
                    )
                )
                + border_col
            )
            for _ in range(self.box_size):
                yield row
        yield from self.border_rows_iter()

    def border_rows_iter(self):
        border_row = [1] * (self.box_size * (self.width + self.border * 2))
        for _ in range(self.border * self.box_size):
            yield border_row


# Keeping this for backwards compatibility.
PymagingImage = PyPNGImage
