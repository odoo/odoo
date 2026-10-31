from odoo import _, models


class PosReportHr(models.Model):
    _inherit = 'pos.report'

    def _get_filter_descriptions(self):
        descriptions = super()._get_filter_descriptions()

        if employee_id := self.env.context.get('employee_id'):
            employees = self.env['hr.employee'].browse(employee_id)
            descriptions.append({
                'label': _('Employee'),
                'value': ', '.join(employees.mapped('display_name')),
            })

        return descriptions

    def _get_export_context(self):
        contexts = super()._get_export_context()

        if employee_id := self.env.context.get('employee_id'):
            employee = self.env['hr.employee'].browse(employee_id)
            for context in contexts:
                context['employee_name'] = employee.display_name
            return contexts

        if not self.env.context.get('employee_wise'):
            return contexts

        handler = self._get_handler()
        orders = self.env['pos.order'].search(handler._get_order_domain())
        employees = orders.mapped('employee_id')

        for employee in employees:
            employee_contexts = self.with_context(employee_id=employee.id)._get_export_context()
            for context in employee_contexts:
                context['employee_name'] = employee.display_name
            contexts.extend(employee_contexts)

        return contexts

    def _get_xlsx_sheet_name(self, export_context):
        return export_context.get('employee_name') or super()._get_xlsx_sheet_name(export_context)
