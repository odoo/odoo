from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(model='account.payment.method')
    def _get_check_printing_payment_method(self, template_code):
        return {
            "check_printing": {
                'name': _('Checks'),
                'code': 'check_printing',
                'payment_type': 'outbound',
            },
        }
