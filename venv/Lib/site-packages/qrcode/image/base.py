import abc
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, Union

from qrcode.image.styles.moduledrawers.base import QRModuleDrawer

if TYPE_CHECKING:
    from qrcode.main import ActiveWithNeighbors, QRCode


DrawerAliases = Dict[str, Tuple[Type[QRModuleDrawer], Dict[str, Any]]]


class BaseImage:
    """
    Base QRCode image output class.
    """

    kind: Optional[str] = None
    allowed_kinds: Optional[Tuple[str]] = None
    needs_context = False
    needs_processing = False
    needs_drawrect = True

    def __init__(self, border, width, box_size, *args, **kwargs):
        self.border = border
        self.width = width
        self.box_size = box_size
        self.pixel_size = (self.width + self.border * 2) * self.box_size
        self.modules = kwargs.pop("qrcode_modules")
        self._img = self.new_image(**kwargs)
        self.init_new_image()

    @abc.abstractmethod
    def drawrect(self, row, col):
        """
        Draw a single rectangle of the QR code.
        """

    def drawrect_context(self, row: int, col: int, qr: "QRCode"):
        """
        Draw a single rectangle of the QR code given the surrounding context
        """
        raise NotImplementedError("BaseImage.drawrect_context")  # pragma: no cover

    def process(self):
        """
        Processes QR code after completion
        """
        raise NotImplementedError("BaseImage.drawimage")  # pragma: no cover

    @abc.abstractmethod
    def save(self, stream, kind=None):
        """
        Save the image file.
        """

    def pixel_box(self, row, col):
        """
        A helper method for pixel-based image generators that specifies the
        four pixel coordinates for a single rect.
        """
        x = (col + self.border) * self.box_size
        y = (row + self.border) * self.box_size
        return (
            (x, y),
            (x + self.box_size - 1, y + self.box_size - 1),
        )

    @abc.abstractmethod
    def new_image(self, **kwargs) -> Any:
        """
        Build the image class. Subclasses should return the class created.
        """

    def init_new_image(self):
        pass

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
            raise ValueError(f"Cannot set {type(self).__name__} type to {kind}")
        return kind

    def is_eye(self, row: int, col: int):
        """
        Find whether the referenced module is in an eye.
        """
        return (
            (row < 7 and col < 7)
            or (row < 7 and self.width - col < 8)
            or (self.width - row < 8 and col < 7)
        )


class BaseImageWithDrawer(BaseImage):
    default_drawer_class: Type[QRModuleDrawer]
    drawer_aliases: DrawerAliases = {}

    def get_default_module_drawer(self) -> QRModuleDrawer:
        return self.default_drawer_class()

    def get_default_eye_drawer(self) -> QRModuleDrawer:
        return self.default_drawer_class()

    needs_context = True

    module_drawer: "QRModuleDrawer"
    eye_drawer: "QRModuleDrawer"

    def __init__(
        self,
        *args,
        module_drawer: Union[QRModuleDrawer, str, None] = None,
        eye_drawer: Union[QRModuleDrawer, str, None] = None,
        **kwargs,
    ):
        self.module_drawer = (
            self.get_drawer(module_drawer) or self.get_default_module_drawer()
        )
        # The eye drawer can be overridden by another module drawer as well,
        # but you have to be more careful with these in order to make the QR
        # code still parseable
        self.eye_drawer = self.get_drawer(eye_drawer) or self.get_default_eye_drawer()
        super().__init__(*args, **kwargs)

    def get_drawer(
        self, drawer: Union[QRModuleDrawer, str, None]
    ) -> Optional[QRModuleDrawer]:
        if not isinstance(drawer, str):
            return drawer
        drawer_cls, kwargs = self.drawer_aliases[drawer]
        return drawer_cls(**kwargs)

    def init_new_image(self):
        self.module_drawer.initialize(img=self)
        self.eye_drawer.initialize(img=self)

        return super().init_new_image()

    def drawrect_context(self, row: int, col: int, qr: "QRCode"):
        box = self.pixel_box(row, col)
        drawer = self.eye_drawer if self.is_eye(row, col) else self.module_drawer
        is_active: Union[bool, ActiveWithNeighbors] = (
            qr.active_with_neighbors(row, col)
            if drawer.needs_neighbors
            else bool(qr.modules[row][col])
        )

        drawer.drawrect(box, is_active)
