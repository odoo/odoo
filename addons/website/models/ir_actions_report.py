# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_report_url(self, layout=None):
        # removes website_id from context to ensure wkhtmltopdf fetches the report assets from this url
        if layout:
            layout = layout.with_context(website_id=False)
        return super(IrActionsReport, self.with_context(website_id=False))._get_report_url(layout=layout)
