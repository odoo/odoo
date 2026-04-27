# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class CommissionAchievement(models.Model):
    _inherit = 'sale.commission.achievement'

    type = fields.Selection(selection_add=[('mrr', "MRR")], ondelete={'mrr': 'cascade'})
