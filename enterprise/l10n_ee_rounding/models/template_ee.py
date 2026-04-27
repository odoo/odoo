from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ee', 'res.company')
    def _get_ee_rounding_res_company(self):
        return {
            self.env.company.id: {
                'l10n_ee_rounding_difference_loss_account_id': 'l10n_ee_6851',
                'l10n_ee_rounding_difference_profit_account_id': 'l10n_ee_431',
            }
        }
