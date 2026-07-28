from decimal import Decimal
try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import qrcode.image.base


class SvgFragmentImage(qrcode.image.base.BaseImage):
    """
    SVG image builder

    Creates a QR-code image as a SVG document fragment.
    """

    _SVG_namespace = "http://www.w3.org/2000/svg"
    kind = "SVG"
    allowed_kinds = ("SVG",)

    def __init__(self, *args, **kwargs):
        ET.register_namespace("svg", self._SVG_namespace)
        super().__init__(*args, **kwargs)
        # Save the unit size, for example the default box_size of 10 is '1mm'.
        self.unit_size = self.units(self.box_size)

    def drawrect(self, row, col):
        self._img.append(self._rect(row, col))

    def units(self, pixels, text=True):
        """
        A box_size of 10 (default) equals 1mm.
        """
        units = Decimal(pixels) / 10
        if not text:
            return units
        return '%smm' % units

    def save(self, stream, kind=None):
        self.check_kind(kind=kind)
        self._write(stream)

    def to_string(self):
        return ET.tostring(self._img)

    def new_image(self, **kwargs):
        return self._svg()

    def _svg(self, tag=None, version='1.1', **kwargs):
        if tag is None:
            tag = ET.QName(self._SVG_namespace, "svg")
        dimension = self.units(self.pixel_size)
        return ET.Element(
            tag, width=dimension, height=dimension, version=version,
            **kwargs)

    def _rect(self, row, col, tag=None):
        if tag is None:
            tag = ET.QName(self._SVG_namespace, "rect")
        x, y = self.pixel_box(row, col)[0]
        return ET.Element(
            tag, x=self.units(x), y=self.units(y),
            width=self.unit_size, height=self.unit_size)

    def _write(self, stream):
        ET.ElementTree(self._img).write(stream, xml_declaration=False)


class SvgImage(SvgFragmentImage):
    """
    Standalone SVG image builder

    Creates a QR-code image as a standalone SVG document.
    """
    background = None

    def _svg(self, tag='svg', **kwargs):
        svg = super()._svg(tag=tag, **kwargs)
        svg.set("xmlns", self._SVG_namespace)
        if self.background:
            svg.append(
                ET.Element(
                    'rect', fill=self.background, x='0', y='0', width='100%',
                    height='100%'))
        return svg

    def _rect(self, row, col):
        return super()._rect(row, col, tag="rect")

    def _write(self, stream):
        ET.ElementTree(self._img).write(stream, encoding="UTF-8",
                                        xml_declaration=True)


class SvgPathImage(SvgImage):
    """
    SVG image builder with one single <path> element (removes white spaces
    between individual QR points).
    """

    QR_PATH_STYLE = {'fill': '#000000', 'fill-opacity': '1',
                     'fill-rule': 'nonzero', 'stroke': 'none'}

    def __init__(self, *args, **kwargs):
        self._points = set()
        super().__init__(*args, **kwargs)

    def _svg(self, viewBox=None, **kwargs):
        if viewBox is None:
            dimension = self.units(self.pixel_size, text=False)
            viewBox = '0 0 {d} {d}'.format(d=dimension)
        return super()._svg(viewBox=viewBox, **kwargs)

    def drawrect(self, row, col):
        # (x, y)
        self._points.add((col, row))

    def _generate_subpaths(self):
        """Generates individual QR points as subpaths"""

        rect_size = self.units(self.box_size, text=False)

        for point in self._points:
            x_base = self.units(
                (point[0]+self.border)*self.box_size, text=False)
            y_base = self.units(
                (point[1]+self.border)*self.box_size, text=False)

            yield (
                'M %(x0)s %(y0)s L %(x0)s %(y1)s L %(x1)s %(y1)s L %(x1)s '
                '%(y0)s z' % dict(
                    x0=x_base, y0=y_base,
                    x1=x_base+rect_size, y1=y_base+rect_size,
                ))

    def make_path(self):
        subpaths = self._generate_subpaths()

        return ET.Element(
            ET.QName("path"),
            d=' '.join(subpaths),
            id="qr-path",
            **self.QR_PATH_STYLE
        )

    def to_string(self):
        img = self._img.__copy__()
        img.append(self.make_path())
        return ET.tostring(img)

    def _write(self, stream):
        self._img.append(self.make_path())
        super()._write(stream)


class SvgFillImage(SvgImage):
    """
    An SvgImage that fills the background to white.
    """
    background = 'white'


class SvgPathFillImage(SvgPathImage):
    """
    An SvgPathImage that fills the background to white.
    """
    background = 'white'
