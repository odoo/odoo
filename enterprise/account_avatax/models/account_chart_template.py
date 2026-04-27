from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('generic_coa', 'account.fiscal.position')
    def _get_us_avatax_fiscal_position(self):
        return {
            'account_fiscal_position_avatax_us': {
                'name': 'Automatic Tax Mapping (AvaTax)',
                'is_avatax': True,
                'auto_apply': False,
                'country_id': self.env.ref('base.us').id,
            },
        }
