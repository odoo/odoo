from odoo import models
from odoo.fields import Domain


class PosSalesDetailReportHr(models.AbstractModel):
    _inherit = 'pos.sales.detail.report'

    def _get_filters(self):
        filters = super()._get_filters()
        filters.append({
            'type': 'single_select', 'key': 'employee_id', 'model': 'hr.employee', 'label': 'Employee',
        })
        return filters

    def _get_pdf_templates(self):
        templates = super()._get_pdf_templates()
        if self.env.ref('pos_hr.pos_report_pdf_header_employee', raise_if_not_found=False):
            templates = {**templates, 'header': 'pos_hr.pos_report_pdf_header_employee'}
        return templates

    def _get_sale_line_domain(self, is_refund=None):
        domain = super()._get_sale_line_domain(is_refund=is_refund)

        if employee_id := self.env.context.get('employee_id'):
            domain &= Domain([('order_id.employee_id', '=', employee_id)])

        return domain

    def _get_order_domain(self, states=('paid', 'done')):
        domain = super()._get_order_domain(states)

        if employee_id := self.env.context.get('employee_id'):
            domain &= Domain([('employee_id', '=', employee_id)])

        return domain
