# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def action_select_mo_to_plan(self):
        res = super().action_select_mo_to_plan()
        res['domain'] = Domain.AND([
            res['domain'],
            Domain('subcontractor_id', '=', False),
        ])
        return res
