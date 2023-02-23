from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('eg', 'account.journal')
    def _get_eg_account_journal(self):
        """ If EGYPT chart, we add 2 new journals TA and IFRS"""
        return {
            "tax_adjustment": {
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "sequence": 1,
                "show_on_dashboard": True,
            },
            "ifrs": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 10,
            },
        }
