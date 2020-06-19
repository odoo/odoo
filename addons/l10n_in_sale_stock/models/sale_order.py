# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('company_id', 'warehouse_id')
    def l10n_in_onchange_company_id(self):
        if self.warehouse_id.l10n_in_sale_journal_id:
            self.l10n_in_journal_id = self.warehouse_id.l10n_in_sale_journal_id.id
        else:
            super().l10n_in_onchange_company_id()
