# -*- coding: utf-8 -*-
from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # Write paperformat and report template used on company
    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        if self in [
            self.env.ref('l10n_de_skr03.l10n_de_chart_template', raise_if_not_found=False),
            self.env.ref('l10n_de_skr04.l10n_chart_de_skr04', raise_if_not_found=False)
        ]:
            company.write({
                'external_report_layout_id': self.env.ref('l10n_din5008.external_layout_din5008').id,
                'paperformat_id': self.env.ref('l10n_din5008.paperformat_euro_din').id
            })
        return res
