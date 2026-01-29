# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PayumoneyCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payumoney = cls._prepare_provider('payumoney', update_values={
            'payumoney_merchant_key': 'dummy',
            'payumoney_merchant_salt': 'dummy',
        })

        # Override default values
        cls.provider = cls.payumoney
        cls.currency = cls._prepare_currency('INR')

        cls.notification_data = {
            'PG_TYPE': 'HDFCPG',
            'addedon': '2022-01-19 21:36:05',
            'address1': '',
            'address2': '',
            'amount': '100.00',
            'amount_split': '{"PAYU":"100.00"}',
            'bank_ref_num': '429387287430473',
            'bankcode': 'VISA',
            'cardhash': 'This field is no longer supported in postback params.',
            'cardnum': '401200XXXXXX1112',
            'city': '',
            'country': '',
            'discount': '0.00',
            'email': 'admin@yourcompany.example.com',
            'encryptedPaymentId': 'A45B5A1E189A9FC89C0E150F2E6EF074',
            'error': 'E000',
            'error_Message': 'No Error',
            'field1': '021268586345',
            'field2': '315728',
            'field3': '429387287430473',
            'field4': 'ejRWR1J6RFRQWnd1c1BXb2FTbVk=',
            'field5': '05',
            'field6': '',
            'field7': 'AUTHPOSITIVE',
            'field8': '',
            'field9': '',
            'firstname': 'Mitchell',
            'giftCardIssued': 'true',
            'hash': '6618df5167d46785efeb0ef392d9a150de0c6e56699eb67898ebc690202fa5fe53cee1290b2ca2dfdc307e5bff2518e30dfa680923b538d7ab7f1624a4a9baa5',
            'isConsentPayment': '0',
            'key': 'GuWsdB4T',
            'lastname': '',
            'mihpayid': '9084338127',
            'mode': 'CC',
            'name_on_card': 'ABC DEF',
            'net_amount_debit': '100',
            'payuMoneyId': '251115271',
            'phone': '5555555555',
            'productinfo': 'anv-test-20220118140529',
            'state': '',
            'status': 'success',
            'txnid': cls.reference,
            'unmappedstatus': 'captured',
            'zipcode': '',
        }
