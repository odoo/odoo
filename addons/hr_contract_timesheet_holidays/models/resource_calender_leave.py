from odoo import models
from odoo.osv import expression


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _get_timesheet_employees(self, employees, leave):
        """ We will Override this method to filter employees for timesheets based on the Contracts.
            By default, returns all employees """

        domain_no_contract = [
            ('id', 'in', employees.ids),
            ('company_id', '=', leave.company_id.id),
            ('contract_ids', '=', False),
        ]

        domain_with_contract = [
            ('id', 'in', employees.ids),
            ('company_id', '=', leave.company_id.id),
            ('contract_ids.state', '=', 'open'),
            ('contract_ids.date_start', '<=', leave.date_from.date()),
            '|',
                ('contract_ids.date_end', '=', False),
                ('contract_ids.date_end', '>=', leave.date_to.date()),
        ]

        domain = expression.OR([domain_no_contract, domain_with_contract])
        return self.env['hr.employee'].search(domain)
