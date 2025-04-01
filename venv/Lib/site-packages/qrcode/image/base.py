class BaseImage(object):
    """
    Base QRCode image output class.
    """
    kind = None
    allowed_kinds = None

    def __init__(self, border, width, box_size, *args, **kwargs):
        self.border = border
        self.width = width
        self.box_size = box_size
        self.pixel_size = (self.width + self.border*2) * self.box_size
        self._img = self.new_image(**kwargs)

    def drawrect(self, row, col):
        """
        Draw a single rectangle of the QR code.
        """
        raise NotImplementedError("BaseImage.drawrect")

    def save(self, stream, kind=None):
        """
        Save the image file.
        """
        raise NotImplementedError("BaseImage.save")

    def pixel_box(self, row, col):
        """
        A helper method for pixel-based image generators that specifies the
        four pixel coordinates for a single rect.
        """
        x = (col + self.border) * self.box_size
        y = (row + self.border) * self.box_size
        return [(x, y), (x + self.box_size - 1, y + self.box_size - 1)]

    def new_image(self, **kwargs):  # pragma: no cover
        """
        Build the image class. Subclasses should return the class created.
        """
        return None

    def get_image(self, **kwargs):
        """
        Return the image class for further processing.
        """
        return self._img

    def check_kind(self, kind, transform=None):
        """
        Get the image type.
        """
        if kind is None:
            kind = self.kind
        allowed = not self.allowed_kinds or kind in self.allowed_kinds
        if transform:
            kind = transform(kind)
            if not allowed:
                allowed = kind in self.allowed_kinds
        if not allowed:
            raise ValueError(
                "Cannot set %s type to %s" % (type(self).__name__, kind))
        return kind
