# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StatementAccountReport(models.AbstractModel):
    _name = 'report.l10n_my_reports.report_statement_account'
    _description = "Statement of Account Report"

    def _get_report_values(self, docids, data=None):
        ids = docids or data['context']['active_ids']
        data['date_to'] = fields.Date.to_date(data.get("date_to", fields.Date.today()))
        return {
            'doc_ids': ids,
            'doc_model': 'res.partner',
            'docs': self.env['res.partner'].browse(ids),
            **data
        }
