# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_in_get_invoice_report_header_values(self):
        values = super()._l10n_in_get_invoice_report_header_values()
        source = self.reversed_entry_id or self
        orders = source.invoice_line_ids.sale_line_ids.order_id.sorted('id')
        if orders:
            order_names = orders.mapped('name')
            values['supplier_reference'] = ', '.join(order_names)
            references = list(dict.fromkeys(filter(None, orders.mapped('client_order_ref'))))
            # An internal SO number is not the buyer's purchase order number.
            internal_references = {*order_names, source.invoice_origin, values['supplier_reference']}
            values['buyer_order_no'] = ', '.join(references) or (
                source.ref if source.ref and source.ref not in internal_references else ''
            )
        return values
