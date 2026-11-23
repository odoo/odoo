# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = 'publisher_warranty.contract'

    @api.model
    def _get_timesheet_activity_query(self):
        # Time off timesheets are generated automatically, they are not an activity of the employee
        return SQL("""
            EXISTS (
                SELECT 1
                  FROM account_analytic_line aal
                 WHERE aal.employee_id = employee.id
                   AND aal.global_leave_id IS NULL
            )
        """)
