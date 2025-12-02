# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class DPOCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dpo = cls._prepare_provider('dpo', update_values={
            'dpo_company_token': '1A2Z3E4R',
            'dpo_service_ref': '1234',
        })

        cls.provider = cls.dpo

        cls.payment_data = {
            'TransID': '123456',
            'CompanyRef': 'Test Transaction',
            'CustomerCreditType': 'VISA',
            'Result': '000',
            'ResultExplanation': 'Success',
        }
