# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.fields import Domain


class ReportPos_HrSingle_Employee_Sales_Report(models.AbstractModel):
    _name = 'report.pos_hr.single_employee_sales_report'
    _inherit = ['report.point_of_sale.report_saledetails']
    _description = 'Session sales details for a single employee'

    def _get_domain(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, employee_id=False):
        domain = super()._get_domain(date_start=date_start, date_stop=date_stop, config_ids=config_ids, session_ids=session_ids)

        if (employee_id):
            domain = Domain.AND([domain, [('employee_id', '=', employee_id)]])

        return domain

    def _prepare_get_sale_details_args_kwargs(self, data):
        args, kwargs = super()._prepare_get_sale_details_args_kwargs(data)
        kwargs['employee_id'] = data.get('employee_id')
        return args, kwargs

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, employee_id=False):
        data = super().get_sale_details(date_start=date_start, date_stop=date_stop, config_ids=config_ids, session_ids=session_ids, employee_id=employee_id)

        if (employee_id):
            employee = self.env['hr.employee'].search([('id', '=', employee_id)])
            data['employee_name'] = employee.name

            # Recalculate invoiceList, invoiceTotal, and total_paid specifically for this employee
            orders = self.env['pos.order'].search(self._get_domain(date_start=date_start, date_stop=date_stop, config_ids=config_ids, session_ids=session_ids, employee_id=employee_id))
            invoiced_orders = orders.filtered(lambda o: o.is_invoiced)
            sessions = orders.mapped('session_id')

            invoice_list = []
            invoice_total = 0
            for session in sessions:
                session_invoiced_orders = invoiced_orders.filtered(lambda o: o.session_id == session)
                if session_invoiced_orders:
                    invoice_list.append({
                        'name': session.name,
                        'invoices': [{
                            'id': order.account_move.id,
                            'total': order.account_move.amount_total_signed,
                            'name': order.account_move.name,
                            'order_ref': order.pos_reference,
                        } for order in session_invoiced_orders],
                    })
                    invoice_total += sum(session_invoiced_orders.mapped('amount_paid'))

            data['invoiceList'] = invoice_list
            data['invoiceTotal'] = invoice_total
            data['total_paid'] = sum(p['total'] for p in data['payments'] if 'total' in p)

        return data
