#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _prepare_project_values(self):
        values = super()._prepare_project_values()
        if len(self.analytic_account_ids) == 1:
            values['analytic_account_id'] = self.analytic_account_ids.id
        return values
