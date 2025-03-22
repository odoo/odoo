# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super()._load(company)
        if company.chart_template_id == self.env.ref('l10n_sg.sg_chart_template'):
            company.write({
                'account_sale_tax_id': self.env.ref(f'l10n_sg.{company.id}_sg_sale_tax_sr_9').id,
                'account_purchase_tax_id': self.env.ref(f'l10n_sg.{company.id}_sg_purchase_tax_tx8_9').id,
            })
        return res
