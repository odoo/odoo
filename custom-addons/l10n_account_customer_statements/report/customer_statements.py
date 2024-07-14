# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.l10n_account_customer_statements.customer_statements'
    _description = "Customer Statements Report"

    def _get_report_values(self, docids, data=None):
        ids = docids or data['context']['active_ids']
        return {
            'doc_ids': ids,
            'doc_model': 'res.partner',
            'docs': self.env['res.partner'].browse(ids),
            'company': self.env.company,
            **data,
        }
