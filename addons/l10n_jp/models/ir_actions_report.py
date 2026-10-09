# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def get_paperformat(self):
        # The Japanese Business layout needs a smaller top margin, unless the report or the company chose its own format.
        paperformat = super().get_paperformat()
        if self.paperformat_id or self.env.company.external_report_layout_id != self.env.ref('l10n_jp.external_layout_jp_standard'):
            return paperformat
        if paperformat and paperformat not in self.env.ref('base.paperformat_euro') | self.env.ref('base.paperformat_us'):
            return paperformat
        return self.env.ref('l10n_jp.paperformat_jp')
