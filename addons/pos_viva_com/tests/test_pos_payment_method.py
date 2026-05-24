# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import MagicMock

import odoo.tests
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestVivaComBearerTokenAcl(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        bank_journal = cls.company_data['default_journal_bank']
        # Only POS administrators may create payment methods (Odoo 19+); test data is not the ACL under test.
        cls.viva_pm = cls.env['pos.payment.method'].sudo().create({
            'name': 'Viva ACL Test',
            'journal_id': bank_journal.id,
            'use_payment_terminal': 'viva_com',
            'viva_com_merchant_id': 'm',
            'viva_com_api_key': 'k',
            'viva_com_client_id': 'test-client-id',
            'viva_com_client_secret': 'test-client-secret',
            'viva_com_terminal_id': '01234543210',
        })
        cls.pos_user = cls.env['res.users'].create({
            'name': 'Pos Only User ACL',
            'login': 'pos_viva_acl_test',
            'password': 'pos_viva_acl_test',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('point_of_sale.group_pos_user').id,
            ])],
        })

    def test_bearer_token_persists_for_pos_user(self):
        """Test POS user can use Viva.com payment method"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'access_token': 'refreshed-token'}
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp

        self.viva_pm.with_user(self.pos_user)._bearer_token(mock_session)

        self.assertEqual(self.viva_pm.viva_com_bearer_token, 'refreshed-token')
