# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_in_get_invoice_partner(self):
        self.ensure_one()
        if line_id := self.sale_id:
            return line_id.partner_invoice_id
        return False

    def _l10n_in_get_fiscal_position(self):
        self.ensure_one()
        if sale_order := self.sale_id:
            return sale_order.fiscal_position_id
        return super()._l10n_in_get_fiscal_position()

    def _l10n_in_related_account_moves(self):
        # We filter out refunds (Credit Note) because, returns should be handled through
        # Pickings and Ewaybill don't support Credit Note as valid document
        if sale_order := self.sale_id:
            return sale_order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
        return super()._l10n_in_related_account_moves()
