# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange('company_id', 'picking_type_id')
    def l10n_in_onchange_company_id(self):
        if self.picking_type_id.warehouse_id and self.picking_type_id.warehouse_id.l10n_in_purchase_journal_id:
            self.l10n_in_journal_id = self.picking_type_id.warehouse_id.l10n_in_purchase_journal_id.id
        else:
            super().l10n_in_onchange_company_id()
