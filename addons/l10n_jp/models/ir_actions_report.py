# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def get_paperformat(self):
        # The Japanese Business layout only fits on a page whose top margin
        # leaves the header band out, so it comes with its own format. A report
        # that pins a format knows what it prints on, and so does a company that
        # moved away from the shipped defaults; neither is overridden here.
        paperformat = super().get_paperformat()
        jp_layout = self.env.ref('l10n_jp.external_layout_jp_standard', raise_if_not_found=False)
        if not jp_layout or self.paperformat_id or self.env.company.external_report_layout_id != jp_layout:
            return paperformat
        default_paperformats = self.env.ref('base.paperformat_euro', raise_if_not_found=False) \
            | self.env.ref('base.paperformat_us', raise_if_not_found=False)
        if paperformat and paperformat not in default_paperformats:
            return paperformat
        return self.env.ref('l10n_jp.paperformat_jp', raise_if_not_found=False) or paperformat
