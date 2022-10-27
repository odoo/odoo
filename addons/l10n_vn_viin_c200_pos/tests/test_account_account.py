from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestAccountAccount(TransactionCase):

    def test_correct_default_pos_receivable_account(self):
        # After install l10n_vn_viin_c200_pos, all pos.payment.method have  receivable_account_id isn't account_default_pos_receivable_account_id 
        # will change to account_default_pos_receivable_account_id
        # Check, If exit pos.payment.method have receivable_account_id isn't account_default_pos_receivable_account_id, this method will throw error
        # This test is only true at the time of new installation
        vn_template = self.env.ref('l10n_vn.vn_template')
        companies = self.env['res.company'].search([('chart_template_id', '=', vn_template.id)])
        for company in companies:
            accounts = company.account_default_pos_receivable_account_id
            pos_payment_method = self.env['pos.payment.method'].search([('company_id', '=', company.id), ('receivable_account_id', '!=', accounts.id)])
            self.assertEqual(len(pos_payment_method), 0, "l10n_vn_viin_c200_pos: Wrong account in PoS Payment Methods." 
                                                        "Note: this test is only true at the time of new installation")
