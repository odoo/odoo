from odoo import _, models
from odoo.fields import Domain

from odoo.addons.point_of_sale.report.pos_report_handler import report_section


class PosSalesDetailReportHr(models.AbstractModel):
    _inherit = 'pos.sales.detail.report'

    def _get_filters(self):
        filters = super()._get_filters()
        filters.append({
            'type': 'single_select', 'key': 'employee_id', 'model': 'hr.employee', 'label': _('Employee'),
        })
        return filters

    def _get_sale_line_domain(self, options, is_refund=None):
        domain = super()._get_sale_line_domain(options, is_refund=is_refund)

        if employee_id := options.get('employee_id'):
            domain &= Domain([('order_id.employee_id', '=', employee_id)])

        return domain

    def _get_order_domain(self, options, states=('paid', 'done')):
        domain = super()._get_order_domain(options, states)

        if employee_id := options.get('employee_id'):
            domain &= Domain([('employee_id', '=', employee_id)])

        return domain

    @report_section(id='session_control', name='Session Control', sequence=50)
    def _section_session_control(self, options):
        # Counted balances belong to the whole session, not an individual employee.
        if options.get('employee_id'):
            return None
        return super()._section_session_control(options)

    def _get_filter_descriptions(self, options):
        descriptions = super()._get_filter_descriptions(options)

        if employee_id := options.get('employee_id'):
            employees = self.env['hr.employee'].browse(employee_id)
            descriptions.append({
                'label': _('Employee'),
                'value': ', '.join(employees.mapped('display_name')),
            })

        return descriptions

    def _get_export_context(self, report, options, export_context):
        if employee_id := options.get('employee_id'):
            employee = self.env['hr.employee'].browse(employee_id)
            export_context.update({
                'employee_name': employee.display_name,
                'xlsx_sheet_name': employee.display_name,
            })

        contexts = super()._get_export_context(report, options, export_context)
        if not options.get('employee_id') and options.get('employee_wise'):
            orders = self.env['pos.order'].search(self._get_order_domain(options))
            for employee in orders.mapped('employee_id'):
                contexts.extend(report._get_export_context({**options, 'employee_id': employee.id}))
        return contexts
