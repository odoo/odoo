# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('company_id', 'warehouse_id')
    def _compute_l10n_in_journal_id(self):
        super()._compute_l10n_in_journal_id()
        for order in self:
            if order.country_code == 'IN':
                if order.warehouse_id.l10n_in_sale_journal_id:
                    order.l10n_in_journal_id = order.warehouse_id.l10n_in_sale_journal_id.id
