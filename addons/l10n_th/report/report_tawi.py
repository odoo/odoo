from odoo import models
from odoo.tools import misc


class Report50Tawi(models.AbstractModel):
    _name = 'report.l10n_th.report_50_tawi'
    _description = '50 Tawi Report'

    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': self.env['account.payment'].browse(docids),
            # The report is intended to be in Thai, but we fall back to English if not enabled
            'report_lang': misc.get_lang(self.env, 'th_TH').code,
            'data': data,
        }
