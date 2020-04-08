# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.payment.tests.common import PaymentAcquirerCommon


@tagged('post_install', '-at_install', '-standard', 'external')
class SipsTest(PaymentAcquirerCommon):

    def setUp(self):
        super().setUp()
        self.sips = self.env.ref('payment.payment_acquirer_sips')

    def test_10_sips_form_render(self):
        self.assertEqual(self.sips.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # render the button
        tx = self.env['payment.transaction'].create({
            'acquirer_id': self.sips.id,
            'amount': 100.0,
            'reference': 'SO404',
            'currency_id': self.currency_euro.id,
        })
        self.sips.render('SO404', 100.0, self.currency_euro.id, values=self.buyer_values).decode('utf-8')

    def test_20_sips_form_management(self):
        self.assertEqual(self.sips.environment, 'test', 'test without test environment')

        # typical data posted by Sips after client has successfully paid
        sips_post_data = {
            'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840|'
                    'merchantId=002001000000001|orderChannel=INTERNET|'
                    'responseCode=00|transactionDateTime=2020-04-08T06:15:59+02:00|'
                    'transactionReference=SO100x1|keyVersion=1|'
                    'acquirerResponseCode=00|amount=31400|authorisationId=0020000006791167|'
                    'paymentMeanBrand=IDEAL|paymentMeanType=CREDIT_TRANSFER|'
                    'customerIpAddress=127.0.0.1|returnContext={"return_url": '
                    '"/payment/process", "reference": '
                    '"SO100x1"}|holderAuthentRelegation=N|holderAuthentStatus=|'
                    'transactionOrigin=INTERNET|paymentPattern=ONE_SHOT|customerMobilePhone=null|'
                    'mandateAuthentMethod=null|mandateUsage=null|transactionActors=null|'
                    'mandateId=null|captureLimitDate=20200408|dccStatus=null|dccResponseCode=null|'
                    'dccAmount=null|dccCurrencyCode=null|dccExchangeRate=null|'
                    'dccExchangeRateValidity=null|dccProvider=null|'
                    'statementReference=SO100x1|panEntryMode=MANUAL|walletType=null|'
                    'holderAuthentMethod=NO_AUTHENT_METHOD',
            'Encode': '',
            'InterfaceVersion': 'HP_2.4',
            'Seal': 'f03f64da6f57c171904d12bf709b1d6d3385131ac914e97a7e1db075ed438f3e',
            'locale': 'en'
        }

        tx = self.env['payment.transaction'].create({
            'amount': 314.0,
            'acquirer_id': self.sips.id,
            'currency_id': self.currency_euro.id,
            'reference': 'SO100x1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        tx.form_feedback(sips_post_data, 'sips')
        self.assertEqual(tx.state, 'done', 'Sips: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, 'SO100x1', 'Sips: validation did not update tx id')
        
        # same process for an payment in error on sips's end
        sips_post_data = {
            'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840|'
                    'merchantId=002001000000001|orderChannel=INTERNET|responseCode=12|'
                    'transactionDateTime=2020-04-08T06:24:08+02:00|transactionReference=SO100x2|'
                    'keyVersion=1|amount=31400|customerIpAddress=127.0.0.1|returnContext={"return_url": '
                    '"/payment/process", "reference": '
                    '"SO100x2"}|paymentPattern=ONE_SHOT|customerMobilePhone=null|mandateAuthentMethod=null|'
                    'mandateUsage=null|transactionActors=null|mandateId=null|captureLimitDate=null|'
                    'dccStatus=null|dccResponseCode=null|dccAmount=null|dccCurrencyCode=null|'
                    'dccExchangeRate=null|dccExchangeRateValidity=null|dccProvider=null|'
                    'statementReference=SO100x2|panEntryMode=null|walletType=null|holderAuthentMethod=null',
            'InterfaceVersion': 'HP_2.4',
            'Seal': '6e1995ea5432580860a04d8515b6eb1507996f97b3c5fa04fb6d9568121a16a2'
        }
        tx = self.env['payment.transaction'].create({
            'amount': 314.0,
            'acquirer_id': self.sips.id,
            'currency_id': self.currency_euro.id,
            'reference': 'SO100x2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})
        tx.form_feedback(sips_post_data, 'sips')
        # check state
        self.assertEqual(tx.state, 'cancel', 'Sips: erroneous validation did not put tx into error state')

    def test_30_sips_badly_formatted_date(self):
        self.assertEqual(self.sips.environment, 'test', 'test without test environment')

        # typical data posted by Sips after client has successfully paid
        bad_date = '2020-04-08T06:15:59+56:00'
        sips_post_data = {
            'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840|'
                    'merchantId=002001000000001|orderChannel=INTERNET|'
                    'responseCode=00|transactionDateTime=%s|'
                    'transactionReference=SO100x1|keyVersion=1|'
                    'acquirerResponseCode=00|amount=31400|authorisationId=0020000006791167|'
                    'paymentMeanBrand=IDEAL|paymentMeanType=CREDIT_TRANSFER|'
                    'customerIpAddress=127.0.0.1|returnContext={"return_url": '
                    '"/payment/process", "reference": '
                    '"SO100x1"}|holderAuthentRelegation=N|holderAuthentStatus=|'
                    'transactionOrigin=INTERNET|paymentPattern=ONE_SHOT|customerMobilePhone=null|'
                    'mandateAuthentMethod=null|mandateUsage=null|transactionActors=null|'
                    'mandateId=null|captureLimitDate=20200408|dccStatus=null|dccResponseCode=null|'
                    'dccAmount=null|dccCurrencyCode=null|dccExchangeRate=null|'
                    'dccExchangeRateValidity=null|dccProvider=null|'
                    'statementReference=SO100x1|panEntryMode=MANUAL|walletType=null|'
                    'holderAuthentMethod=NO_AUTHENT_METHOD' % (bad_date,),
            'Encode': '',
            'InterfaceVersion': 'HP_2.4',
            'Seal': 'f03f64da6f57c171904d12bf709b1d6d3385131ac914e97a7e1db075ed438f3e',
            'locale': 'en'
        }

        tx = self.env['payment.transaction'].create({
            'amount': 314.0,
            'acquirer_id': self.sips.id,
            'currency_id': self.currency_euro.id,
            'reference': 'SO100x1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        tx.form_feedback(sips_post_data, 'sips')
        self.assertEqual(tx.state, 'done', 'Sips: validation did not put tx into done state when date format was weird')
