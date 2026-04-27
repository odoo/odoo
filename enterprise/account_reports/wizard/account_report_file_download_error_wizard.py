# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountReportFileDownloadErrorWizard(models.TransientModel):
    _name = 'account.report.file.download.error.wizard'
    _description = "Manage the file generation errors from report exports."

    actionable_errors = fields.Json()
    file_name = fields.Char()
    file_content = fields.Binary()

    def button_download(self):
        self.ensure_one()
        if self.file_name:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/account.report.file.download.error.wizard/{self.id}/file_content/{self.file_name}?download=1',
                'close': True,
            }
