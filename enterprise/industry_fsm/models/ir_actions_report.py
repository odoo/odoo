from odoo import models, _
from odoo.exceptions import ValidationError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if self._get_report(report_ref).report_name == 'industry_fsm.worksheet_custom':
            tasks = self.env['project.task'].browse(res_ids).filtered('display_satisfied_conditions_count')
            if tasks:
                return super()._render_qweb_pdf(report_ref, res_ids=tasks.ids, data=data)
            else:
                raise ValidationError(_('The field service report is unavailable for the selected tasks as they do not contain any timesheets, products, or worksheets.'))
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
