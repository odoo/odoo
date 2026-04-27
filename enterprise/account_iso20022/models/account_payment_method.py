# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, osv


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['sepa_ct'] = {
            'mode': 'multi',
            'type': ('bank',),
            'currency_ids': self.env.ref("base.EUR").ids,
        }
        res['iso20022'] = {
            'mode': 'multi',
            'type': ('bank',),
        }
        res['iso20022_se'] = {
            'mode': 'multi',
            'type': ('bank',),
            'currency_ids': self.env.ref("base.SEK").ids,
        }
        res['iso20022_ch'] = {
            'mode': 'multi',
            'type': ('bank',),
            'currency_ids': self.env.ref("base.CHF").ids,
        }
        return res

    def _get_payment_method_domain(self, code, with_currency=True, with_country=True):
        domain = super()._get_payment_method_domain(code, with_currency, with_country)
        if with_currency and code == 'iso20022':
            # To prevent ISO20022 to be automatically added to the journals to which SEPA has to be added when updating
            # the payment methods of the existing journals, at module install
            eur_currency = self.env.ref("base.EUR")
            domain = osv.expression.AND([domain, [
                '|',
                '&', ('currency_id', '=', False), ('company_id.currency_id', '!=', eur_currency.id),
                '&', ('currency_id', '!=', False), ('currency_id', '!=', eur_currency.id),
            ]])
        return domain
