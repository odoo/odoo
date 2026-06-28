from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def get_paperformat(self):
        paper_format = super().get_paperformat()
        din5008_formats = self.env['report.paperformat'].search([('name', 'ilike', '%din5008%')])
        if self.env.context.get('account_report_pdf_export') and paper_format in din5008_formats:
            return self.env.ref('base.paperformat_euro')
        return paper_format
