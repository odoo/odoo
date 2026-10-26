# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = 'publisher_warranty.contract'

    @api.model
    def _get_activity_filters(self):
        return []

    @api.model
    def _get_message(self):
        msg = super()._get_message()
        employee_query = self.env["hr.employee"]._search([
            ('active', '=', True),
            '|', ('user_id', '=', False),
                '|', ('user_id.active', '=', False),
                     ('user_id.share', '=', True),
        ])
        activity_queries = self._get_activity_filters()
        # If not module that link activities to employees, all employees without user are free
        if not activity_queries:
            activity_query = SQL("FALSE")
        else:
            activity_query = SQL(" OR ").join(activity_queries)

        sql = SQL(
            """
            SELECT count(employee.id)
              FROM hr_employee employee
             WHERE employee.id IN %s
               AND (%s)
            """,
            employee_query.subselect(),
            activity_query,
        )
        self.env.cr.execute(sql)
        msg['nbr_employees_wo_user'] = self.env.cr.fetchone()[0]
        return msg
