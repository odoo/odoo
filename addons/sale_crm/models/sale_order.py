# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons import (sale, crm)


class SaleOrder(sale.models.SaleOrder):

    opportunity_id = fields.Many2one(
        crm.models.Lead, string='Opportunity', check_company=True,
        domain="[('type', '=', 'opportunity'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def action_confirm(self):
        return super(SaleOrder, self.with_context({k: v for k, v in self._context.items() if k != 'default_tag_ids'})).action_confirm()
