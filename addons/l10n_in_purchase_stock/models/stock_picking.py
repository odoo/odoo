# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _compute_l10n_in_related_invoice_ids(self):
        super()._compute_l10n_in_related_invoice_ids()
        for picking in self:
            if picking.purchase_id and picking.purchase_id.invoice_ids:
                picking.l10n_in_related_invoice_ids = picking.purchase_id.invoice_ids
