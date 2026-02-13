# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class MollieCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mollie = cls._prepare_provider('mollie', update_values={
            'mollie_api_key': 'dummy',
        })
        cls.provider = cls.mollie
        cls.currency = cls.currency_euro

        cls.payment_data = {
            'ref': cls.reference,
            'id': 'tr_ABCxyz0123',
            'status': 'paid',
            'mandateId': 'mdt_test123',
        }
        cls.payment_method = cls.env['payment.method'].create({
            'name': 'Mollie Credit Card',
            'code': 'creditcard',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test User',
            'email': 'test@example.com',
        })
        cls.tx = cls.env['payment.transaction'].create({
            'reference': 'TEST123',
            'amount': 10.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'provider_id': cls.provider.id,
            'partner_id': cls.partner.id,
            'payment_method_id': cls.payment_method.id,
        })
