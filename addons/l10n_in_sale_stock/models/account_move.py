# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_in_get_invoice_report_header_values(self):
        values = super()._l10n_in_get_invoice_report_header_values()
        pickings = self.invoice_line_ids.sale_line_ids.move_ids.filtered(
            lambda move: move.state == 'done' and move.picking_id.picking_type_id.code == 'outgoing'
        ).picking_id.sorted('id')
        values['delivery_notes'] = pickings.mapped('name')
        values['delivery_note_dates'] = [fields.Date.to_date(picking.date_done) for picking in pickings]
        return values

    def _l10n_in_get_warehouse_address(self):
        res = super()._l10n_in_get_warehouse_address()
        if self.invoice_line_ids.sale_line_ids:
            company_shipping_id = self.mapped("invoice_line_ids.sale_line_ids.order_id.warehouse_id.partner_id")
            if len(company_shipping_id) == 1:
                return company_shipping_id
        return res
