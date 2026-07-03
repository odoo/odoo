# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_l10n_in_dropship_dest_partner(self):
        self.ensure_one()
        if line_id := self.purchase_id:
            return line_id.dest_address_id
        return False

    def _l10n_in_get_fiscal_position(self):
        self.ensure_one()
        if purchase_order := self.purchase_id:
            purchase_order.fiscal_position_id
        return super()._l10n_in_get_fiscal_position()

    def _l10n_in_related_account_moves(self):
        if purchase_order := self.purchase_id:
            # We filter out refunds (Credit Note) because, returns should be handled through
            # Pickings and Ewaybill don't support Credit Note as valid document
            return purchase_order.invoice_ids.filtered(lambda m: m.move_type == 'in_invoice')
        return super()._l10n_in_related_account_moves()
