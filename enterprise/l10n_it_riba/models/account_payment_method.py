from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        return {
            **super()._get_payment_method_information(),
            'riba': {
                'mode': 'multi',
                'country_id': self.env.ref('base.it').id,
                'domain': [('type', '=', 'bank')]
            }
        }
