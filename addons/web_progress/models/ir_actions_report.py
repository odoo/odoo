# Part of web_progress. See LICENSE file for full copyright and licensing details.
from odoo import models, api, registry, fields, _


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_template(self, template, values=None):
        """
        Add progress_iter to the context in order to track progress of iterations inside report generation method
        """
        if 'progress_code' in self._context and values and 'docs' in values:
            new_values = values.copy()
            new_values['docs'] = self.web_progress_iter(values.get('docs'), "Generating HTML")
        else:
            new_values = values
        return super(IrActionsReport, self)._render_template(template, values=new_values)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """
        Add progress_iter to the context in order to track progress of iterations inside report generation method
        """
        self.web_progress_percent(30, 'Rendering PDF')
        self = self.with_context(progress_iter=True)
        return super(IrActionsReport, self)._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        self.web_progress_percent(90, 'Merging PDF')
        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
