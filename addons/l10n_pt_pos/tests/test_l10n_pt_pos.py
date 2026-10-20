from odoo import Command, fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.models import Model
from odoo.tests import tagged
from odoo.tests.common import freeze_time
from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nPtPosCommon(TestL10nPtCommon, TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # A PT PoS order is always invoiced, and the invoice is the signed document: an order with a
        # customer becomes an invoice-receipt (FR), issued in the series of the PoS invoice journal.
        cls.fr_series = cls.env['l10n_pt.at.series'].create({
            'name': '2024',
            'company_id': cls.company_pt.id,
            'training_series': True,
            'company_exclusive_series': True,
            'date_start': '2024-01-01',
            'date_end': '2024-12-31',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice_receipt',
            'prefix': 'FR',
            'at_code': 'AT-TESTFR2024',
        })
        category_pt = cls.env['pos.category'].create({'name': 'Test Category'})
        cls.config = cls.basic_config
        cls.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set(category_pt.ids)],
        })
        cls.config.payment_method_ids.write({
            'l10n_pt_pos_payment_mechanism': 'TB',
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'default_code': 'P1',
            'list_price': 100,
            'taxes_id': cls.tax_sale_0.ids,
            'pos_categ_ids': [Command.link(category_pt.id)],
        })

    def _create_pos_order(self, date_order="2024-01-01", partner=False):
        order_data = self.create_ui_order_data(
            pos_order_lines_ui_args=[
                (self.product1, 1.0),
            ],
            customer=partner or self.partner_a,
            is_invoiced=True,
        )
        results = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(results['pos.order'][0]['id'])
        order.action_pos_order_paid()
        if date_order:
            # Bypass the write method of pos.order to change the date_order
            Model.write(order, {'date_order': fields.Date.from_string(date_order)})
        return order


@freeze_time('2024-06-15')
@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtPosHash(TestL10nPtPosCommon):
    def test_l10n_pt_pos_hash_inalterability(self):
        """The invoice generated from a PoS order is signed when the order is synced, and locked."""
        self.open_new_session()
        move = self._create_pos_order().account_move
        self.assertEqual(move.l10n_pt_document_type, 'out_invoice_receipt')
        self.assertTrue(move.inalterable_hash)

        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:.*"
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Invoice/Bill Date"):
            move.invoice_date = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Document Number"):
            move.l10n_pt_document_number = "New number/0001"

    def test_l10n_pt_pos_hash_integrity_report(self):
        """The integrity report verifies the chain of the invoices generated from PoS orders."""
        self.open_new_session()
        moves = self.env['account.move']
        for date_order in ("2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"):
            moves |= self._create_pos_order(date_order).account_move

        def integrity_check():
            return next(
                result for result in self.company_pt._check_hash_integrity()['results']
                if f"({moves[0].sequence_prefix}...)" in result['journal_name']
            )

        self.assertEqual(integrity_check()['status'], 'verified')

        # Change one of the fields used by the signature, bypassing the write lock of account.move.
        Model.write(moves[2], {'invoice_date': fields.Date.from_string('2024-01-07')})
        self.assertEqual(integrity_check()['status'], 'corrupted')
        self.assertEqual(
            integrity_check()['msg_cover'],
            f'Corrupted data on journal entry with id {moves[2].id} ({moves[2].name}).',
        )


@freeze_time('2024-06-15')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPosMiscRequirements(TestL10nPtPosCommon):
    def test_l10n_pt_pos_partner(self):
        """Test misc requirements for partner"""
        self.open_new_session()
        # Cannot change tax number of an existing client with already issued documents.
        # However, missing tax number can only be entered if the field is empty
        # (or filled with generic client tax 999999990)
        partner_a = self.env['res.partner'].create({
            'name': 'Partner A',
            'company_id': self.company_pt.id,
        })
        partner_a.vat = "PT123456789"
        partner_a.vat = "999999990"

        self._create_pos_order(partner=partner_a)

        partner_a.vat = "PT123456789"
        with self.assertRaisesRegex(UserError, "You cannot change the VAT number of a partner that already has issued documents"):
            partner_a.vat = "PT987654321"

    def test_l10n_pt_pos_product(self):
        """Test that we do not allow change ProductDescription if already issued docs"""
        self.open_new_session()
        product = self.product1
        product.name = "Product A2"  # OK

        self._create_pos_order()

        with self.assertRaisesRegex(UserError, "You cannot modify the name of a product that has been used"):
            # Stock picking is triggered before POS order
            product.name = "Product A3"

    def test_l10n_pt_pos_payment_method(self):
        """
        Test that we do not allow opening a session if some of the payment methods do not have a payment mechanism or
        if a bank journal payment method has no AT Series (required to create the payment entry when PoS session is
        closed).
        """
        pos_payment_method = self.env['pos.payment.method'].create({
            'name': 'Payment method - No mechanism',
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.config.write({'payment_method_ids': [Command.link(pos_payment_method.id)]})
        with self.assertRaisesRegex(RedirectWarning, "All payment methods available for this Point of Sale should have a payment mechanism"):
            self.open_new_session()
