# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ch', 'res.company')
    def _get_ch_res_company(self):
        company_data = super()._get_ch_res_company()
        company_data[self.env.company.id].update({
            'external_report_layout_id': 'l10n_din5008.external_layout_din5008',
            'paperformat_id': 'l10n_din5008.paperformat_euro_din',
        })
        return company_data
