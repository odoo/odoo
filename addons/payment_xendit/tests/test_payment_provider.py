from odoo.tests import tagged
from unittest.mock import patch

from odoo.addons.payment_xendit.tests.common import XenditCommon

@tagged('post_install', '-at_install')
class TestPaymentProvider(XenditCommon):
    def test_incompatible_with_unsupported_currencies(self):
        """Ensure xendit only shows up given the supported currencies"""
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.xendit, compatible_providers)

    def test_xendit_api(self):
        """Ensure API request is only called once when running '_xendit_make_request'"""
        data = {
            'external_id': 'TEST0001',
            'amount': '100000'
        }
        with patch('requests.request') as mock_request:
            self.xendit._xendit_make_request('INVOICE', payload=data)
            mock_request.assert_called_once()
