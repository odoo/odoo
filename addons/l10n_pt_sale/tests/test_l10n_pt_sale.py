from freezegun import freeze_time
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.models import Model
from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.sale.tests.common import TestSaleCommon


class TestL10nPtSaleCommon(TestL10nPtCommon, TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for index, series in enumerate([cls.series_2017, cls.series_2024]):
            series.write({
                'at_series_line_ids': [
                    Command.create({'type': 'quotation', 'prefix': 'OR', 'at_code': f'AT-TESTQUOT-{index}'}),
                    Command.create({'type': 'sales_order', 'prefix': 'NE', 'at_code': f'AT-TESTSO-{index}'}),
                ],
            })

    def create_quotation(self, date_order="2024-01-01", l10n_pt_hashed_on=None, amount=1000.0, tax=None,
                         partner=None, product=False, company=None):
        quotation_data = {
            'company_id': company.id if company else self.company_pt.id,
            'partner_id': (partner or self.partner_a).id,
            'date_order': fields.Date.from_string(date_order),
            'order_line': [Command.create({
                'product_id': (product or self.company_data['product_order_no']).id,
                'product_uom_qty': 1,
                'price_unit': amount,
                'tax_id': [tax.id if tax else self.tax_sale_23.id],
            })]
        }

        if quotation_data['date_order'].year not in ('2017', '2024'):
            quotation_data['l10n_pt_at_series_id'] = self.series_2024.id

        quotation = self.env['sale.order'].with_company(company or self.company_pt).create(quotation_data)
        return quotation

    def create_sales_order(self, date_order="2024-01-01", l10n_pt_hashed_on=None, amount=1000.0, tax=None,
                           partner=None, product=False, do_hash=False, company=None):
        quotation = self.create_quotation(date_order, l10n_pt_hashed_on, amount, tax, partner, product, company)

        quotation.action_l10n_pt_create_sales_order()
        sales_order = quotation.sales_order_ids
        sales_order.date_order = fields.Date.from_string(date_order)

        if do_hash:
            with freeze_time(l10n_pt_hashed_on):
                self.env['sale.order']._l10n_pt_compute_missing_hashes(company or self.company_pt)
        return quotation.sales_order_ids


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtSaleHashing(TestL10nPtSaleCommon):
    def test_l10n_pt_sale_hash_sequence(self):
        """
        Test that the hash sequence is correct.
        For this, we use the following resource provided by the Portuguese tax authority:
        https://info.portaldasfinancas.gov.pt/apps/saft-pt01/local/saft_idemo599999999.xml
        We create invoices with the same info as in the link, and we check that the hash that we obtain in Odoo
        is the same as the one given in the link (using the same sample keys).
        """

        l10n_pt_document_number = ""

        def _get_l10n_pt_document_number_patched(self_patched):
            return l10n_pt_document_number

        with patch(
            'odoo.addons.l10n_pt_sale.models.sale_order.SaleOrder._get_l10n_pt_sale_document_number',
            _get_l10n_pt_document_number_patched,
        ):
            for (l10n_pt_document_number, date_order, l10n_pt_hashed_on, amount, expected_hash) in [
                ('COF E1/1', '2017-09-13', '2017-09-13T16:34:56', 56.54, "0Z5205QyulzTiunymKhw4QY98kKWfohYzd+79pMujoRBItru0uDWtj6vQyLumInI5kUsvnGB/SMjRU1iqj1iEaumPwqqpgeZReEgH/9b2pOfoahBAt8vocnFOM/NxvDOoiYa61vz9zGdWZzWjDv1NWxQpYSNercF8PrQm0m0UtA="),
                ('COF E1/2', '2017-09-14', '2017-09-14T09:23:23', 548.10, "rzdj0UZfMWjUMTq+Ge1LUK3YeGxDTPEcUUTH9lVzizFnM6PB9fHpYxS7IvLc5CbBHZlldAEOv/6CcxFoE8RNoa8XOGaQbYAptHD0hEsUvMxlh23CuHiKRQVac9bDMiS1FAjrBcXA29w6DHpaVRO285PAR1RZBhnGC3j4DPzcyCo="),
            ]:
                with self.subTest(date_order=date_order, l10n_pt_hashed_on=l10n_pt_hashed_on, amount=amount, expected_hash=expected_hash):
                    so = self.create_sales_order(date_order, l10n_pt_hashed_on, amount, self.tax_sale_0, do_hash=True)
                    so.flush_recordset()
                    self.assertEqual(so.l10n_pt_sale_inalterable_hash.split("$")[2], expected_hash)

    def test_l10n_pt_sale_hash_inalterability(self):
        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:*"

        so = self.create_sales_order('2024-01-01', do_hash=True)
        so.flush_recordset()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.l10n_pt_sale_inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.date_order = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.l10n_pt_hashed_on = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.amount_total = 666
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.name = "new name"
        with self.assertRaisesRegex(UserError, expected_error_msg):
            so.l10n_pt_document_number = "new number/0001"

        # The following field is not part of the hash so it can be modified
        so.validity_date = fields.Date.from_string('2000-01-01')

    def test_l10n_pt_sale_hash_integrity_report(self):
        """Test the hash integrity report"""
        sales_order1 = self.create_sales_order('2024-01-03', do_hash=True)
        quotation1 = sales_order1.quotation_id
        self.create_sales_order('2024-01-04', do_hash=True)
        sales_order3 = self.create_sales_order('2024-01-05', do_hash=True)
        quotation3 = sales_order3.quotation_id

        integrity_check = self.company_pt._l10n_pt_sale_check_hash_integrity()['results']

        integrity_check_quot = integrity_check[0]  # [0] = 2024 Quotation series
        self.assertEqual(integrity_check_quot['status'], 'verified')
        self.assertRegex(integrity_check_quot['msg_cover'], 'Quotations are correctly hashed')
        self.assertEqual(integrity_check_quot['first_date'], quotation1.date_order)
        self.assertEqual(integrity_check_quot['last_date'], quotation3.date_order)

        integrity_check_so = integrity_check[1]  # [1] = 2024 SO series
        self.assertEqual(integrity_check_so['status'], 'verified')
        self.assertRegex(integrity_check_so['msg_cover'], 'Sales Orders are correctly hashed')
        self.assertEqual(integrity_check_so['first_date'], sales_order1.date_order)
        self.assertEqual(integrity_check_so['last_date'], sales_order3.date_order)

        # Change one of the fields used by the hash.
        Model.write(sales_order1, {'date_order': fields.Date.from_string('2024-01-07')})
        integrity_check = self.company_pt._l10n_pt_sale_check_hash_integrity()['results'][1]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(
            integrity_check['msg_cover'],
            f'Corrupted data on sales order with id {sales_order1.id} ({sales_order1.l10n_pt_document_number}).',
        )

        # Let's try with the l10n_pt_sale_inalterable_hash field itself
        Model.write(sales_order1, {'date_order': fields.Date.from_string("2024-01-03")})  # Revert the previous change
        Model.write(sales_order3, {'l10n_pt_sale_inalterable_hash': 'fake_hash'})
        integrity_check = self.company_pt._l10n_pt_sale_check_hash_integrity()['results'][1]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on sales order with id {sales_order3.id} ({sales_order3.l10n_pt_document_number}).')


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtSaleMiscRequirements(TestL10nPtSaleCommon):
    def test_l10n_pt_sale_document_no(self):
        """
        Test that the document number for quotations and sales orders in Portugal
        follows this format: [^ ]+ [^/^ ]+/[0-9]+
        """
        so1 = self.create_sales_order('2024-01-01')
        quotation = self.create_quotation('2024-01-01')
        quotation.action_l10n_pt_create_sales_order()
        so2 = quotation.sales_order_ids
        so2.date_order = fields.Date.from_string('2024-01-02')
        so2.action_cancel()  # shouldn't change the document number
        so3 = self.create_sales_order('2024-01-03', do_hash=True)

        self.assertEqual(so1.quotation_id._get_l10n_pt_sale_document_number(), 'OR 2024/00001')
        self.assertEqual(so1._get_l10n_pt_sale_document_number(), 'NE 2024/00001')
        self.assertEqual(quotation._get_l10n_pt_sale_document_number(), 'OR 2024/00002')
        self.assertEqual(so2._get_l10n_pt_sale_document_number(), 'NE 2024/00002')
        self.assertEqual(so3.quotation_id._get_l10n_pt_sale_document_number(), 'OR 2024/00003')
        self.assertEqual(so3._get_l10n_pt_sale_document_number(), 'NE 2024/00003')

    def test_l10n_pt_sale_lines(self):
        """
        Test that sale orders without taxes or negative lines cannot be created
        """
        with self.assertRaisesRegex(UserError, "You cannot create a line without VAT tax."):
            self.env['sale.order'].with_company(self.company_pt).create({
                'company_id': self.company_pt.id,
                'partner_id': self.partner_a.id,
                'date_order': fields.Date.from_string('2024-02-04'),
                'order_line': [
                    Command.create({
                        'product_id': self.company_data['product_order_no'].id,
                        'product_uom_qty': 1,
                        'price_unit': 1000,
                        'tax_id': [],
                    }),
                ],
            })

        with self.assertRaisesRegex(UserError, "You cannot create a Quotation with negative lines on it"):
            self.create_quotation(amount=-10)

    def test_l10n_pt_sale_partner(self):
        """Test misc requirements for partner"""
        partner_a = self.env['res.partner'].create({
            'name': 'Partner A',
            'company_id': self.company_pt.id,
        })
        partner_a.vat = "PT123456789"
        partner_a.vat = "999999990"  # Can change tax number, since no documents issued for this partner

        self.create_sales_order(partner=partner_a, do_hash=True)
        # Missing tax number, or filled with generic client tax 999999990, can be changed
        partner_a.vat = "PT123456789"
        # Once the tax number is filled/not the generic one, and client has issued documents, vat can't be changed
        with self.assertRaisesRegex(UserError, "partner that already has issued documents"):
            partner_a.vat = "PT987654321"

    def test_l10n_pt_sale_product(self):
        """
        Test that we do not allow changes to the ProductDescription if product is used in already issued docs
        """
        product = self.company_data['product_order_no']
        product.name = "Product A2"  # OK

        self.create_sales_order(product=product, do_hash=True)

        with self.assertRaisesRegex(UserError, "You cannot modify the name of a product that has been used"):
            product.name = "Product A3"

    def test_l10n_pt_date_order_validation(self):
        """
        Test that, if a quotation has a future date, no other quotation can be issued a document number in the
        same series. The document number is set when the quotation is either sent, previewed or confirmed.
        """
        self.create_quotation(fields.Date.today() + timedelta(days=1))
        quotation = self.create_quotation(fields.Date.today())
        with self.assertRaisesRegex(UserError, "You cannot create a quotation or sales order with a date earlier than"):
            # _checks_l10n_pt_sales_order() is called when the quotation is sent, previewed or confirmed
            quotation.action_l10n_pt_create_sales_order()

    def test_l10n_pt_sale_discount(self):
        """
        Test that global and line discounts are applied correctly in quotations, sale orders and in
        invoices created from a SO.
        """
        quotation = self.env['sale.order'].with_company(self.company_pt).create({
            'company_id': self.company_pt.id,
            'partner_id': self.partner_a.id,
            'date_order': fields.Date.from_string('2024-02-04'),
            'l10n_pt_global_discount': 10.0,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 1234.568,
                    'l10n_pt_line_discount': 10.0,
                    'tax_id': self.tax_sale_23.ids,
                }),
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 756.81,
                    'tax_id': self.tax_sale_23.ids,
                }),
            ],
        })
        quotation.action_l10n_pt_create_sales_order()

        sale_order = quotation.sales_order_ids
        self.assertEqual(sale_order.amount_total, 2067.79, 'Total amount with discounts is wrong')

        move = quotation.sales_order_ids._create_invoices()
        self.assertInvoiceValues(move, [
            {
                'price_unit': 1234.57,
                'price_subtotal': 1000.00,
                'price_total': 1230.00,
                'debit': 0.0,
                'credit': 1000.0,
            },
            {
                'price_unit': 756.81,
                'price_subtotal': 681.13,
                'price_total': 837.79,
                'debit': 0.0,
                'credit': 681.13,
            },
            {
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'debit': 0.0,
                'credit': 386.66,
            },
            {
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'debit': 2067.79,
                'credit': 0.0,
            },
        ], {
             'amount_untaxed': 1681.13,
             'amount_tax': 386.66,
             'amount_total': 2067.79,
         })
