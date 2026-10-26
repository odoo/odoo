# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = 'publisher_warranty.contract'

    @api.model
    def _get_activity_filters(self):
        activity_queries = super()._get_activity_filters()
        activity_queries.append(
            SQL("EXISTS (SELECT 1 FROM account_analytic_line aal WHERE aal.employee_id = employee.id)")
        )
        return activity_queries
