# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _compute_l10n_in_related_invoice_ids(self):
        super()._compute_l10n_in_related_invoice_ids()
        for picking in self:
            if picking.sale_id and picking.sale_id.invoice_ids:
                picking.l10n_in_related_invoice_ids = picking.sale_id.invoice_ids

    def _compute_l10n_in_has_linked_with_sale_purchase(self):
        super()._compute_l10n_in_has_linked_with_sale_purchase()
        for picking in self:
            if picking.sale_id:
                picking.l10n_in_has_linked_with_sale_purchase = True

    def _l10n_in_create_invoice(self):
        super()._l10n_in_create_invoice()
        if self.sale_id:
            return self.sale_id._create_invoices()
