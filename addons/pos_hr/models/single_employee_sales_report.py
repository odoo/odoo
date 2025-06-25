# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.osv.expression import AND


class SingleEmployeeSalesReport(models.AbstractModel):
    _name = 'report.pos_hr.single_employee_sales_report'
    _inherit = 'report.point_of_sale.report_saledetails'
    _description = 'Session sales details for a single employee'

    def _get_domain(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, employee_id=False):
        domain = super()._get_domain(config_ids=config_ids, session_ids=session_ids)

        if (employee_id):
            domain = AND([domain, [('employee_id', '=', employee_id)]])

        return domain

    def _prepare_get_sale_details_args_kwargs(self, data):
        args, kwargs = super()._prepare_get_sale_details_args_kwargs(data)
        kwargs['employee_id'] = data.get('employee_id')
        return args, kwargs

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, employee_id=False):
        data = super().get_sale_details(config_ids=config_ids, session_ids=session_ids, employee_id=employee_id)

        if (employee_id):
            employee = self.env['hr.employee'].search([('id', '=', employee_id)])
            data['employee_name'] = employee.name

        return data
