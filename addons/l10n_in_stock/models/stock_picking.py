# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_in_related_invoice_ids = fields.Many2many('account.move', string="Invoices",
        compute="_compute_l10n_in_related_invoice_ids")
    l10n_in_related_invoice_id = fields.Many2one('account.move', string="Invoice", copy=False)
    l10n_in_has_linked_with_sale_purchase = fields.Boolean(compute="_compute_l10n_in_has_linked_with_sale_purchase")

    def _compute_l10n_in_related_invoice_ids(self):
        # TO OVERRIDE in sale and purchase
        for picking in self:
            picking.l10n_in_related_invoice_ids = []

    def _compute_l10n_in_has_linked_with_sale_purchase(self):
        # TO OVERRIDE in sale and purchase
        for picking in self:
            picking.l10n_in_has_linked_with_sale_purchase = False

    def _l10n_in_create_invoice(self):
        # TO OVERRIDE in sale and purchase
        return False

    def _should_generate_commercial_invoice(self):
        super(StockPicking, self)._should_generate_commercial_invoice()
        return True
