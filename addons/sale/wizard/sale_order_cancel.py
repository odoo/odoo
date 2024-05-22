# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderCancel(models.TransientModel):
    _name = 'sale.order.cancel'
    _description = "Sales Order Cancel"

    order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    display_invoice_alert = fields.Boolean('Invoice Alert', compute='_compute_display_invoice_alert')

    @api.depends('order_id')
    def _compute_display_invoice_alert(self):
        for wizard in self:
            wizard.display_invoice_alert = bool(wizard.order_id.invoice_ids.filtered(lambda inv: inv.state == 'draft'))

    def action_cancel(self):
        return self.order_id.with_context({'disable_cancel_warning': True}).action_cancel()
