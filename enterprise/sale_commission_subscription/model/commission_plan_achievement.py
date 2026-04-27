# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    type = fields.Selection(selection_add=[('mrr', "MRR")], ondelete={'mrr': 'cascade'})
    recurring_plan_id = fields.Many2one('sale.subscription.plan', string="Recurring Plan")

    @api.constrains('type', 'product_id', 'product_categ_id')
    def _constrains_type_mrr(self):
        for pa in self:
            if pa.type == 'mrr' and (pa.product_id or pa.product_categ_id):
                raise UserError(_("You cannot have Product or Category constraints on MRR achievements."))
            elif pa.type in ['amount_sold', 'qty_sold'] and pa.recurring_plan_id:
                raise UserError(_("You cannot have Recurring Plan constraint on SO achievements."))
