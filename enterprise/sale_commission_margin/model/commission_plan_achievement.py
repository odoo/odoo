# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class CommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    type = fields.Selection(selection_add=[('margin', "Margin")], ondelete={'margin': 'cascade'})
