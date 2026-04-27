# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class ChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cl', 'res.company')
    def _get_cl_res_company(self):
        res = super()._get_cl_res_company()
        res[self.env.company.id].update({
            'l10n_cl_factoring_journal_id': 'general',
            'l10n_cl_factoring_counterpart_account_id': 'account_110315',
        })
        return res
