# coding: utf-8

from odoo import api, fields, models

# Force the API version to avoid breaking in case of update on Stripe side
# cf https://stripe.com/docs/api#versioning
# changelog https://stripe.com/docs/upgrades#api-changelog
STRIPE_HEADERS = {'Stripe-Version': '2016-03-07'}


class PaymentAcquirerStripe(models.Model):
    _inherit = 'payment.acquirer'

    stripe_secret_key = fields.Char(required_if_provider='stripe')
    stripe_publishable_key = fields.Char(required_if_provider='stripe')
    stripe_image_url = fields.Char("Checkout Image URL",
        help="A relative or absolute URL pointing to a square image of your "
             "brand or product. As defined in your Stripe profile. See: "
             "https://stripe.com/docs/checkout")

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirerStripe, self)._get_providers()
        providers.append(['stripe', 'Stripe'])
        return providers

    @api.multi
    def stripe_form_generate_values(self, tx_values):
        self.ensure_one()
        stripe_tx_values = dict(tx_values)
        temp_stripe_tx_values = {
            'amount': tx_values.get('amount'),
            'currency': tx_values.get('currency') and tx_values.get('currency').name or '',
            'address_line1': tx_values['partner_address'],
            'address_city': tx_values['partner_city'],
            'address_country': tx_values['partner_country'] and tx_values['partner_country'].name or '',
            'email': tx_values['partner_email'],
            'address_zip': tx_values['partner_zip'],
            'name': tx_values['partner_name'],
            'phone': tx_values['partner_phone'],
        }

        temp_stripe_tx_values['returndata'] = stripe_tx_values.pop('return_url', '')
        stripe_tx_values.update(temp_stripe_tx_values)
        return stripe_tx_values

    @api.model
    def _get_stripe_api_url(self):
        return 'api.stripe.com/v1'

    @api.model
    def stripe_s2s_form_process(self, data):
        payment_token = self.env['payment.token'].sudo().create({
            'cc_number': data['cc_number'],
            'cc_holder_name': data['cc_holder_name'],
            'cc_expiry': data['cc_expiry'],
            'cc_brand': data['cc_brand'],
            'cvc': data['cvc'],
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id'])
        })
        return payment_token.id

    @api.multi
    def stripe_s2s_form_validate(self, data):
        self.ensure_one()

        # mandatory fields
        for field_name in ["cc_number", "cvc", "cc_holder_name", "cc_expiry", "cc_brand"]:
            if not data.get(field_name):
                return False
        return True
