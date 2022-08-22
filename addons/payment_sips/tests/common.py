# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class SipsCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sips = cls._prepare_acquirer('sips', update_values={
            'sips_merchant_id': 'dummy_mid',
            'sips_secret': 'dummy_secret',
        })

        # Override default values
        cls.acquirer = cls.sips
        cls.currency = cls.currency_euro

        cls.notification_data = {
            'Data': f'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840'
                    f'|merchantId=002001000000001|orderChannel=INTERNET|responseCode=00'
                    f'|transactionDateTime=2022-01-19T18:01:06+01:00'
                    f'|transactionReference={cls.reference}'
                    f'|keyVersion=1|acquirerResponseCode=00|amount=10000|authorisationId=12345'
                    f'|guaranteeIndicator=Y|cardCSCResultCode=4D|panExpiryDate=202201'
                    f'|paymentMeanBrand=VISA|paymentMeanType=CARD|customerIpAddress=111.11.111.11'
                    f'|maskedPan=4100##########00|returnContext={{"reference": "{cls.reference}"}}'
                    f'|holderAuthentRelegation=N|holderAuthentStatus=3D_SUCCESS'
                    f'|tokenPan=dp528b9xwknujmkw|transactionOrigin=INTERNET|paymentPattern=ONE_SHOT'
                    f'|customerMobilePhone=null|mandateAuthentMethod=null|mandateUsage=null'
                    f'|transactionActors=null|mandateId=null|captureLimitDate=20220119'
                    f'|dccStatus=null|dccResponseCode=null|dccAmount=null|dccCurrencyCode=null'
                    f'|dccExchangeRate=null|dccExchangeRateValidity=null|dccProvider=null'
                    f'|statementReference=tx20220119170050|panEntryMode=MANUAL|walletType=null'
                    f'|holderAuthentMethod=NOT_SPECIFIED',
            'Encode': '',
            'InterfaceVersion': 'HP_2.4',
            'Seal': '8a4c1f8b268832600a7bf40ddaa5d487f07d61dea81b8119ab8bab3c8a0861f3',
            'locale': 'en',
        }
