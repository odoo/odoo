# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request, content_disposition
from odoo.tools import pdf


class DeliveryController(http.Controller):

    @http.route('/print/shipping/<picking_ids>', type='http', auth='user')
    def print_shipping_lables(self, picking_ids):
        pickings = request.env['stock.picking'].browse([int(picking_id) for picking_id in picking_ids.split(',')])
        content = pdf.merge_pdf([attachment.raw for attachment in pickings.picking_label_ids])
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition('shippingLabels.pdf'))
        ]
        return request.make_response(content, headers)
