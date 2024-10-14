import decimal
from decimal import Decimal
from typing import List, Optional, Type, Union, overload, Literal

import qrcode.image.base
from qrcode.compat.etree import ET
from qrcode.image.styles.moduledrawers import svg as svg_drawers
from qrcode.image.styles.moduledrawers.base import QRModuleDrawer


class SvgFragmentImage(qrcode.image.base.BaseImageWithDrawer):
    """
    SVG image builder

    Creates a QR-code image as a SVG document fragment.
    """

    _SVG_namespace = "http://www.w3.org/2000/svg"
    kind = "SVG"
    allowed_kinds = ("SVG",)
    default_drawer_class: Type[QRModuleDrawer] = svg_drawers.SvgSquareDrawer

    def __init__(self, *args, **kwargs):
        ET.register_namespace("svg", self._SVG_namespace)
        super().__init__(*args, **kwargs)
        # Save the unit size, for example the default box_size of 10 is '1mm'.
        self.unit_size = self.units(self.box_size)

    @overload
    def units(self, pixels: Union[int, Decimal], text: Literal[False]) -> Decimal: ...

    @overload
    def units(self, pixels: Union[int, Decimal], text: Literal[True] = True) -> str: ...

    def units(self, pixels, text=True):
        """
        A box_size of 10 (default) equals 1mm.
        """
        units = Decimal(pixels) / 10
        if not text:
            return units
        units = units.quantize(Decimal("0.001"))
        context = decimal.Context(traps=[decimal.Inexact])
        try:
            for d in (Decimal("0.01"), Decimal("0.1"), Decimal("0")):
                units = units.quantize(d, context=context)
        except decimal.Inexact:
            pass
        return f"{units}mm"

    def save(self, stream, kind=None):
        self.check_kind(kind=kind)
        self._write(stream)

    def to_string(self, **kwargs):
        return ET.tostring(self._img, **kwargs)

    def new_image(self, **kwargs):
        return self._svg(**kwargs)

    def _svg(self, tag=None, version="1.1", **kwargs):
        if tag is None:
            tag = ET.QName(self._SVG_namespace, "svg")
        dimension = self.units(self.pixel_size)
        return ET.Element(
            tag,  # type: ignore
            width=dimension,
            height=dimension,
            version=version,
            **kwargs,
        )

    def _write(self, stream):
        ET.ElementTree(self._img).write(stream, xml_declaration=False)


class SvgImage(SvgFragmentImage):
    """
    Standalone SVG image builder

    Creates a QR-code image as a standalone SVG document.
    """

    background: Optional[str] = None
    drawer_aliases: qrcode.image.base.DrawerAliases = {
        "circle": (svg_drawers.SvgCircleDrawer, {}),
        "gapped-circle": (svg_drawers.SvgCircleDrawer, {"size_ratio": Decimal(0.8)}),
        "gapped-square": (svg_drawers.SvgSquareDrawer, {"size_ratio": Decimal(0.8)}),
    }

    def _svg(self, tag="svg", **kwargs):
        svg = super()._svg(tag=tag, **kwargs)
        svg.set("xmlns", self._SVG_namespace)
        if self.background:
            svg.append(
                ET.Element(
                    "rect",
                    fill=self.background,
                    x="0",
                    y="0",
                    width="100%",
                    height="100%",
                )
            )
        return svg

    def _write(self, stream):
        ET.ElementTree(self._img).write(stream, encoding="UTF-8", xml_declaration=True)


class SvgPathImage(SvgImage):
    """
    SVG image builder with one single <path> element (removes white spaces
    between individual QR points).
    """

    QR_PATH_STYLE = {
        "fill": "#000000",
        "fill-opacity": "1",
        "fill-rule": "nonzero",
        "stroke": "none",
    }

    needs_processing = True
    path: Optional[ET.Element] = None
    default_drawer_class: Type[QRModuleDrawer] = svg_drawers.SvgPathSquareDrawer
    drawer_aliases = {
        "circle": (svg_drawers.SvgPathCircleDrawer, {}),
        "gapped-circle": (
            svg_drawers.SvgPathCircleDrawer,
            {"size_ratio": Decimal(0.8)},
        ),
        "gapped-square": (
            svg_drawers.SvgPathSquareDrawer,
            {"size_ratio": Decimal(0.8)},
        ),
    }

    def __init__(self, *args, **kwargs):
        self._subpaths: List[str] = []
        super().__init__(*args, **kwargs)

    def _svg(self, viewBox=None, **kwargs):
        if viewBox is None:
            dimension = self.units(self.pixel_size, text=False)
            viewBox = "0 0 {d} {d}".format(d=dimension)
        return super()._svg(viewBox=viewBox, **kwargs)

    def process(self):
        # Store the path just in case someone wants to use it again or in some
        # unique way.
        self.path = ET.Element(
            ET.QName("path"),  # type: ignore
            d="".join(self._subpaths),
            id="qr-path",
            **self.QR_PATH_STYLE,
        )
        self._subpaths = []
        self._img.append(self.path)


class SvgFillImage(SvgImage):
    """
    An SvgImage that fills the background to white.
    """

    background = "white"


class SvgPathFillImage(SvgPathImage):
    """
    An SvgPathImage that fills the background to white.
    """

    background = "white"
