# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiPredict(TestItEdi):
    """ Main test class for the l10n_it_edi vendor bills XML import"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.italian_partner_c = cls.env['res.partner'].create({
            'company_id': cls.company.id,
            'is_company': True,
            'country_id': cls.env.ref('base.it').id,
            'name': 'NOT Alessi',
            'vat': 'IT00313371213',
            'l10n_it_codice_fiscale': '93026890017',
            'street': 'Via Privata NOT Alessi 6',
            'zip': '28887',
            'city': 'Milan',
        })

        cls.tax_purchase_c = cls.company_data_2['default_tax_purchase']
        cls.tax_purchase_c.amount = 22
        cls.tax_purchase_d = cls.safe_copy(cls.tax_purchase_c)
        cls.tax_purchase_d.amount = 10

        cls.purchase_journal = cls.company_data_2['default_journal_purchase']
        cls.expense_account = cls.purchase_journal.default_account_id
        cls.predictable_account = cls.env['account.account'].with_company(cls.company).create({
            'name': 'Predictable expense',
            'code': '410999',
            'account_type': 'expense',
        })

        cls.product_c = cls.env['product.product'].with_company(cls.company).create({
            'name': 'Cool stuff',
            'standard_price': 123.00,
            'supplier_taxes_id': [fields.Command.set(cls.tax_purchase_c.ids)],
        })


    def _create_predictable_invoice(self):
        # Creates an invoice to base the prediction on
        predictable_invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'partner_id': self.italian_partner_c.id,
            'invoice_date': fields.Date.from_string('2023-05-01'),
            'journal_id': self.purchase_journal.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_c.id,
                    'quantity': 1.0,
                    'tax_ids': [fields.Command.set([self.tax_purchase_c.id])],
                    'account_id': self.predictable_account.id,
                }), (0, 0, {
                    'name': 'OtherAccount',
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'tax_ids': [fields.Command.set([self.tax_purchase_c.id])],
                    'account_id': self.predictable_account.id,
                }), (0, 0, {
                    'name': 'GuessTaxes',
                    'quantity': 2.0,
                    'price_unit': 8.0,
                    'tax_ids': [fields.Command.set([self.tax_purchase_d.id])],
                    'account_id': self.predictable_account.id,
                }),
            ]
        })
        predictable_invoice.action_post()

    def test_receive_vendor_bill_with_prediction(self):
        """
            - First line has both product and account predicted
            - Second line has account predicted
            - Third line has both tax and account predicted
        """
        self._create_predictable_invoice()
        self.company.predict_bill_product = True

        self._assert_import_invoice(
            'IT01234567888_FPR01.xml', [{
                'invoice_date': fields.Date.from_string('2014-12-18'),
                'amount_untaxed': 39.0,
                'amount_tax': 7.38,
                'invoice_line_ids': [{
                    'product_id': self.product_c.id,
                    'name': 'Cool stuff',
                    'account_id': self.predictable_account.id,
                    'quantity': 5.0,
                    'price_unit': 1.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'OtherAccount',
                    'account_id': self.predictable_account.id,
                    'quantity': 3.0,
                    'price_unit': 8.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'GuessTaxes',
                    'account_id': self.predictable_account.id,
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'tax_ids': [self.tax_purchase_d.id]
                }],
            }])

    def test_receive_vendor_bill_without_product_prediction(self):
        self._create_predictable_invoice()
        self.company.predict_bill_product = False

        self._assert_import_invoice(
            'IT01234567888_FPR01.xml', [{
                'invoice_date': fields.Date.from_string('2014-12-18'),
                'amount_untaxed': 39.0,
                'amount_tax': 7.38,
                'invoice_line_ids': [{
                    'product_id': False,
                    'name': 'Cool stuff',
                    'account_id': self.predictable_account.id,
                    'quantity': 5.0,
                    'price_unit': 1.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'OtherAccount',
                    'account_id': self.predictable_account.id,
                    'quantity': 3.0,
                    'price_unit': 8.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'GuessTaxes',
                    'account_id': self.predictable_account.id,
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'tax_ids': [self.tax_purchase_d.id]
                }],
            }])

    def test_receive_vendor_bill_without_prediction(self):
        """
            As no previous matching invoice exists,
            no prediction should be made thus no product is found.
            Accounts are just the default for the journal.
            Third line doesn't have a tax in the XML,
            so no tax is added. Real XMLs always have a tax,
            even if that tax has a 0% amount.
        """
        self.company.predict_bill_product = True

        self._assert_import_invoice(
            'IT01234567888_FPR01.xml', [{
                'invoice_date': fields.Date.from_string('2014-12-18'),
                'amount_untaxed': 39.0,
                'amount_tax': 6.38,
                'invoice_line_ids': [{
                    'product_id': False,
                    'name': 'Cool stuff',
                    'account_id': self.expense_account.id,
                    'quantity': 5.0,
                    'price_unit': 1.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'OtherAccount',
                    'account_id': self.expense_account.id,
                    'quantity': 3.0,
                    'price_unit': 8.0,
                    'tax_ids': [self.tax_purchase_c.id]
                }, {
                    'product_id': False,
                    'name': 'GuessTaxes',
                    'account_id': self.expense_account.id,
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'tax_ids': []
                }],
            }])
