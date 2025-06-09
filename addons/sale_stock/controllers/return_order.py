# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    @route(
        '/return/order/content',
        type='jsonrpc', auth='user', website=True, readonly=True
    )
    def return_order_content(self, order_id, access_token):
        try:
            sale_order = self._document_check_access(
                'sale.order', order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        return_data = {
            'company_name': sale_order.company_id.name,
            'warehouse_address': sale_order.warehouse_id.partner_id._display_address(
                without_company=True,
            ),
            'products': [],
            'reasons': [{
                'id': reason.id,
                'name': reason.name,
            } for reason in request.env['return.reason'].search([])],
        }
        for line in sale_order.order_line:
            if not line._is_returnable():
                continue

            common_line_vals = {
                'name': line.product_id.with_context(display_default_code=False).display_name,
                'currency': line.currency_id.id,
                'description_sale': line.name,
                'price': line.price_unit,
                'product_id': line.product_id.id,
            }

            for move in line.move_ids:
                picking = move.picking_id
                if (
                    picking.picking_type_id.code == 'outgoing'
                    and picking.state == 'done'
                ):
                    returned_moved = picking.return_ids.move_ids.filtered(
                        lambda m: (
                            move in m.move_orig_ids
                            and m.picking_id.state == 'done'
                        )
                    )
                    remaining_delivered_qty = (
                        move.quantity - sum(returned_moved.mapped('quantity'))
                    )
                    if remaining_delivered_qty:
                        returnable_line_vals = {
                            **common_line_vals,
                            'delivery_id': picking.id,
                            'delivery_name': picking.name,
                            'delivered_qty': remaining_delivered_qty,
                            'lot_name': (
                                ', '.join(move.lot_ids.mapped('name')) if move.lot_ids else False
                            ),
                        }
                        return_data['products'].append(returnable_line_vals)

        return return_data

    @route('/my/orders/return_order/download_label', type='http', auth="user")
    def return_order_dowload_label(
        self, order_id, access_token=False, selected_products='', return_reason=''
    ):
        """Download return data of picking for selected products."""
        try:
            sale_order = self._document_check_access(
                'sale.order', int(order_id), access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        selected_products_list = json.loads(selected_products)
        selected_products_per_delivery = defaultdict(dict)
        for product_data in selected_products_list:
            selected_products_per_delivery[product_data['delivery_id']][
                product_data['product_id']
            ] = product_data['quantity']

        return_data = {
            'wh_address_id': sale_order.warehouse_id.partner_id,
            'selected_products_per_delivery': selected_products_per_delivery,
            'return_reason': self.env['return.reason'].browse(int(return_reason)),
        }

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'sale_stock.action_report_return_slip',
            list(selected_products_per_delivery.keys()), data=return_data,
        )[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
