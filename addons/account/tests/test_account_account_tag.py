# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccountAccountTag(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref=None)

    def test_changing_debit_credit(self):
        '''
            Ensure that that after adding manually the tax grids and changing the debit or credit,
            the tax grid persist and not initialized
        '''
        tax_tag = self.env['account.account.tag'].create({
            'name': "test_misc_custom_tags",
            'applicability': 'taxes',
            'country_id': self.env.ref('base.us').id,
        })
        am = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2023-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_tag_ids': tax_tag
                }),
                (0, 0, {
                    'name': 'line_credit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_tag_ids': tax_tag
                }),
            ],
        })

        with self.assertRaises(UserError):
            am.line_ids[0].write({
                'debit': 100,
                'account_id': self.company_data['default_account_assets'].id,
                })
            am.line_ids[1].write({
                'credit': 100,
                'account_id': self.company_data['default_account_expense'].id
                })
        self.assertEqual(am.line_ids[0].tax_tag_ids, tax_tag)
        self.assertEqual(am.line_ids[1].tax_tag_ids, tax_tag)
