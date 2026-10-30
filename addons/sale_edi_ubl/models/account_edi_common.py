from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = 'account.edi.common'

    def _get_line_trade_references(self, vals, base_line):
        # EXTENDS account_edi_ubl_cii
        references = super()._get_line_trade_references(vals, base_line)
        line = base_line['record']
        if not isinstance(line, models.BaseModel) or line._name != 'account.move.line':
            return references

        sale_lines = line.sale_line_ids
        ship_to = sale_lines.order_id.partner_shipping_id
        if len(ship_to) == 1:
            references['ship_to'] = ship_to

        # The customer's order, only needed per line when the invoice groups several orders.
        order = sale_lines.order_id
        invoice_orders = line.move_id.invoice_line_ids.sale_line_ids.order_id
        if len(order) == 1 and order.client_order_ref and len(invoice_orders) > 1:
            references['order_ref'] = order.client_order_ref
        return references
