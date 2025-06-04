# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from lxml import etree
from base64 import b64encode

from odoo.http import request, Response
from odoo import http, tools, _
from odoo.tools.misc import file_open
from odoo.tools.image import image_data_uri, binary_to_image


logger = logging.getLogger(__name__)

class Html_Builder(http.Controller):
    @http.route(['/html_builder/image_shape/<string:img_key>/<module>/<path:filename>'], type='http', auth="public", website=True)
    def image_shape(self, module, filename, img_key, **kwargs):
        svg = self._get_shape_svg(module, 'image_shapes', filename)

        record = request.env['ir.binary']._find_record(img_key)
        stream = request.env['ir.binary']._get_image_stream_from(record)
        if stream.type == 'url':
            return stream.get_response()

        image = stream.read()
        img = binary_to_image(image)
        width, height = tuple(str(size) for size in img.size)
        root = etree.fromstring(svg)

        if root.attrib.get("data-forced-size"):
            # Adjusts the SVG height to ensure the image fits properly within
            # the SVG (e.g. for "devices" shapes).
            svgHeight = float(root.attrib.get("height"))
            svgWidth = float(root.attrib.get("width"))
            svgAspectRatio = svgWidth / svgHeight
            height = str(float(width) / svgAspectRatio)

        root.attrib.update({'width': width, 'height': height})
        # Update default color palette on shape SVG.
        svg, _ = self._update_svg_colors(kwargs, etree.tostring(root, pretty_print=True).decode('utf-8'))
        # Add image in base64 inside the shape.
        uri = image_data_uri(b64encode(image))
        svg = svg.replace('<image xlink:href="', '<image xlink:href="%s' % uri)

        return request.make_response(svg, [
            ('Content-type', 'image/svg+xml'),
            ('Cache-control', 'max-age=%s' % http.STATIC_CACHE_LONG),
        ])
