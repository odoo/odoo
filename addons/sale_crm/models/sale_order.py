# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', check_company=True, index='btree_not_null',
        domain="[('type', '=', 'opportunity'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def action_confirm(self):
        res = super(SaleOrder, self.with_context({k: v for k, v in self.env.context.items() if k != 'default_tag_ids'})).action_confirm()
        for order in self:
            order.opportunity_id._update_revenues_from_so(order)
        return res
