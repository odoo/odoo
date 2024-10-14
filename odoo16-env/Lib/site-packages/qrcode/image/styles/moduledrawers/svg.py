import abc
from decimal import Decimal
from typing import TYPE_CHECKING, NamedTuple

from qrcode.image.styles.moduledrawers.base import QRModuleDrawer
from qrcode.compat.etree import ET

if TYPE_CHECKING:
    from qrcode.image.svg import SvgFragmentImage, SvgPathImage

ANTIALIASING_FACTOR = 4


class Coords(NamedTuple):
    x0: Decimal
    y0: Decimal
    x1: Decimal
    y1: Decimal
    xh: Decimal
    yh: Decimal


class BaseSvgQRModuleDrawer(QRModuleDrawer):
    img: "SvgFragmentImage"

    def __init__(self, *, size_ratio: Decimal = Decimal(1), **kwargs):
        self.size_ratio = size_ratio

    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)
        self.box_delta = (1 - self.size_ratio) * self.img.box_size / 2
        self.box_size = Decimal(self.img.box_size) * self.size_ratio
        self.box_half = self.box_size / 2

    def coords(self, box) -> Coords:
        row, col = box[0]
        x = row + self.box_delta
        y = col + self.box_delta

        return Coords(
            x,
            y,
            x + self.box_size,
            y + self.box_size,
            x + self.box_half,
            y + self.box_half,
        )


class SvgQRModuleDrawer(BaseSvgQRModuleDrawer):
    tag = "rect"

    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)
        self.tag_qname = ET.QName(self.img._SVG_namespace, self.tag)

    def drawrect(self, box, is_active: bool):
        if not is_active:
            return
        self.img._img.append(self.el(box))

    @abc.abstractmethod
    def el(self, box): ...


class SvgSquareDrawer(SvgQRModuleDrawer):
    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)
        self.unit_size = self.img.units(self.box_size)

    def el(self, box):
        coords = self.coords(box)
        return ET.Element(
            self.tag_qname,  # type: ignore
            x=self.img.units(coords.x0),
            y=self.img.units(coords.y0),
            width=self.unit_size,
            height=self.unit_size,
        )


class SvgCircleDrawer(SvgQRModuleDrawer):
    tag = "circle"

    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)
        self.radius = self.img.units(self.box_half)

    def el(self, box):
        coords = self.coords(box)
        return ET.Element(
            self.tag_qname,  # type: ignore
            cx=self.img.units(coords.xh),
            cy=self.img.units(coords.yh),
            r=self.radius,
        )


class SvgPathQRModuleDrawer(BaseSvgQRModuleDrawer):
    img: "SvgPathImage"

    def drawrect(self, box, is_active: bool):
        if not is_active:
            return
        self.img._subpaths.append(self.subpath(box))

    @abc.abstractmethod
    def subpath(self, box) -> str: ...


class SvgPathSquareDrawer(SvgPathQRModuleDrawer):
    def subpath(self, box) -> str:
        coords = self.coords(box)
        x0 = self.img.units(coords.x0, text=False)
        y0 = self.img.units(coords.y0, text=False)
        x1 = self.img.units(coords.x1, text=False)
        y1 = self.img.units(coords.y1, text=False)

        return f"M{x0},{y0}H{x1}V{y1}H{x0}z"


class SvgPathCircleDrawer(SvgPathQRModuleDrawer):
    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)

    def subpath(self, box) -> str:
        coords = self.coords(box)
        x0 = self.img.units(coords.x0, text=False)
        yh = self.img.units(coords.yh, text=False)
        h = self.img.units(self.box_half - self.box_delta, text=False)
        x1 = self.img.units(coords.x1, text=False)

        # rx,ry is the centerpoint of the arc
        # 1? is the x-axis-rotation
        # 2? is the large-arc-flag
        # 3? is the sweep flag
        # x,y is the point the arc is drawn to

        return f"M{x0},{yh}A{h},{h} 0 0 0 {x1},{yh}A{h},{h} 0 0 0 {x0},{yh}z"
