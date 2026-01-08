# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaypalCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.paypal = cls._prepare_provider('paypal', update_values={
            'paypal_email_account': 'dummy@test.mail.com',
        })

        # Override default values
        cls.provider = cls.paypal
        cls.currency = cls.currency_euro

        cls.notification_data = {
            'PayerID': '59XDVNACRAZZK',
            'address_city': 'Scranton',
            'address_country_code': 'US',
            'address_name': 'Mitchell Admin',
            'address_state': 'Pennsylvania',
            'address_street': '215 Vine St',
            'address_zip': '18503',
            'first_name': 'Norbert',
            'handling_amount': '0.00',
            'item_name': 'YourCompany: Test Transaction',
            'item_number': cls.reference,
            'last_name': 'Buyer',
            'mc_currency': cls.currency.name,
            'mc_fee': '2.00',
            'mc_gross': str(cls.amount),
            'notify_version': 'UNVERSIONED',
            'payer_email': 'test-buyer@mail.odoo.com',
            'payer_id': '59XDVNACRAZZK',
            'payer_status': 'VERIFIED',
            'payment_date': '2022-01-19T08:38:06Z',
            'payment_fee': '2.00',
            'payment_gross': '50.00',
            'payment_status': 'Completed',
            'payment_type': 'instant',
            'protection_eligibility': 'ELIGIBLE',
            'quantity': '1',
            'receiver_id': 'BEQE89VH6257B',
            'residence_country': 'US',
            'shipping': '0.00',
            'txn_id': '1H89255869624041K',
            'txn_type': 'web_accept',
            'verify_sign': 'dummy',
        }
