# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class SipsCommon(PaymentCommon):

    NOTIFICATION_DATA = {
        'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840'
                '|merchantId=002001000000001|orderChannel=INTERNET|responseCode=00'
                '|transactionDateTime=2022-01-19T18:01:06+01:00'
                '|transactionReference=Test Transaction'  # Shamefully copy-pasted from payment
                '|keyVersion=1|acquirerResponseCode=00|amount=10000|authorisationId=12345'
                '|guaranteeIndicator=Y|cardCSCResultCode=4D|panExpiryDate=202201'
                '|paymentMeanBrand=VISA|paymentMeanType=CARD|customerIpAddress=111.11.111.11'
                '|maskedPan=4100##########00|returnContext={"reference": "Test Transaction"}'
                '|holderAuthentRelegation=N|holderAuthentStatus=3D_SUCCESS'
                '|tokenPan=dp528b9xwknujmkw|transactionOrigin=INTERNET|paymentPattern=ONE_SHOT'
                '|customerMobilePhone=null|mandateAuthentMethod=null|mandateUsage=null'
                '|transactionActors=null|mandateId=null|captureLimitDate=20220119|dccStatus=null'
                '|dccResponseCode=null|dccAmount=null|dccCurrencyCode=null|dccExchangeRate=null'
                '|dccExchangeRateValidity=null|dccProvider=null|statementReference=tx20220119170050'
                '|panEntryMode=MANUAL|walletType=null|holderAuthentMethod=NOT_SPECIFIED',
        'Encode': '',
        'InterfaceVersion': 'HP_2.4',
        'Seal': '8a4c1f8b268832600a7bf40ddaa5d487f07d61dea81b8119ab8bab3c8a0861f3',
        'locale': 'en',
    }

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.sips = cls._prepare_acquirer('sips', update_values={
            'sips_merchant_id': 'dummy_mid',
            'sips_secret': 'dummy_secret',
        })

        # Override default values
        cls.acquirer = cls.sips
        cls.currency = cls.currency_euro
