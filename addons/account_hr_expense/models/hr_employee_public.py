from odoo import models
from odoo.fields import Domain


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    def _search_filter_for_expense(self, operator, value):
        if operator == 'in' and self.env.user.has_groups('account.group_account_user'):
            return Domain('company_id', '=', False) | Domain('company_id', 'child_of', self.env.company.root_id.id)
        return super()._search_filter_for_expense(operator, value)
