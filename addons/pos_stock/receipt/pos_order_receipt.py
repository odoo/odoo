# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    @api.model
    def get_receipt_template_for_pos_frontend(self):
        names = [
            'point_of_sale.pos_order_receipt_header',
            'point_of_sale.pos_order_receipt_style',
            'pos_stock.pos_orderline_receipt_information',
            'point_of_sale.pos_orderline_receipt',
            'pos_stock.pos_order_receipt_footer',
            'point_of_sale.pos_order_receipt',
        ]
        return [[name, self.env['ir.qweb']._get_template(name)[1]] for name in names]

    def _order_receipt_generate_line_data(self):
        lines_fields = self.env['pos.order.line']._load_pos_data_fields(self.config_id)
        product_fields = self.env['product.product']._load_pos_data_fields(self.config_id)
        products = self.lines.product_id.with_context(display_default_code=False).read(product_fields, load=False)
        product_by_id = {product['id']: product for product in products}

        lines = []
        for line in self.lines:
            data = line.read(lines_fields, load=False)[0]
            display_price_incl = line.order_id.config_id.iface_tax_included == 'total'

            data['qty'] = int(line.qty) if float(line.qty).is_integer() else line.qty
            data['product_data'] = product_by_id[data['product_id']]
            data['lot_names'] = line.pack_lot_ids.mapped('lot_name') if line.pack_lot_ids else False
            data['product_uom_name'] = line.product_id.uom_id.name
            data['price_subtotal_incl'] = self._order_receipt_format_currency(data['price_subtotal_incl'])

            # Compute line unit price
            taxes = line._compute_amount_line_all(1)
            line_unit_price = taxes['price_subtotal_incl'] if display_price_incl else taxes['price_subtotal']
            data['unit_price'] = self._order_receipt_format_currency(line_unit_price)

            # Compute product unit price
            taxes = line.tax_ids.compute_all(data['product_data']['lst_price'], line.order_id.currency_id, 1)
            product_unit_price = taxes['total_included'] if display_price_incl else taxes['total_excluded']
            data['product_unit_price'] = self._order_receipt_format_currency(product_unit_price)

            lines.append(data)

        return lines
