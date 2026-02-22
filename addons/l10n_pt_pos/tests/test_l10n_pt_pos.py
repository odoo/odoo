from odoo import Command, fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.models import Model
from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nPtPosCommon(TestL10nPtCommon, TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['l10n_pt.at.series.line'].create({
            'at_series_id': cls.series_2024.id,
            'type': 'pos_order',
            'prefix': 'POS',
            'at_code': 'AT-TESTPOS',
        })
        category_pt = cls.env['pos.category'].create({'name': 'Test Category'})
        cls.config = cls.basic_config
        cls.config.write({
            'l10n_pt_pos_at_series_id': cls.series_2024.id,
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set(category_pt.ids)],
        })
        cls.config.payment_method_ids.write({
            'l10n_pt_pos_payment_mechanism': 'TB',
            'l10n_pt_pos_default_at_series_id': cls.series_2024.id,
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'list_price': 100,
            'taxes_id': cls.tax_sale_0.ids,
            'pos_categ_ids': [Command.link(category_pt.id)],
        })

    def _create_pos_order(self, date_order="2024-01-01", partner=False):
        order_data = self.create_ui_order_data(
            pos_order_lines_ui_args=[
                (self.product1, 1.0),
            ],
            payments=[(self.bank_pm1, 50.0)],
            customer=partner
        )
        results = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(results['pos.order'][0]['id'])
        order.action_pos_order_paid()
        if date_order:
            # Bypass the write method of pos.order to change the date_order
            Model.write(order, {'date_order': fields.Date.from_string(date_order)})
        return order


@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtPosHash(TestL10nPtPosCommon):
    def test_l10n_pt_pos_hash_inalterability(self):
        self.open_new_session()
        order = self._create_pos_order()
        self.assertEqual(order.l10n_pt_pos_inalterable_hash, False)
        order.l10n_pt_pos_compute_missing_hashes(order.config_id.id)  # Called when printing the receipt

        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:.*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Inalterability Hash."):
            order.l10n_pt_pos_inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Date."):
            order.date_order = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Hashed On."):
            order.l10n_pt_hashed_on = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Order Ref."):
            order.name = "New name"
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Document Number."):
            order.l10n_pt_document_number = "New number/0001"

        # The following field is not part of the hash so it can be modified
        order.general_note = 'new note'

    def test_l10n_pt_pos_hash_integrity_report(self):
        """Test the hash integrity report"""
        self.open_new_session()
        order1 = self._create_pos_order("2024-01-01")
        self._create_pos_order("2024-01-02")
        order3 = self._create_pos_order("2024-01-03")
        order4 = self._create_pos_order("2024-01-04")
        self.assertEqual(order1.l10n_pt_pos_inalterable_hash, False)
        order1.l10n_pt_pos_compute_missing_hashes(order1.config_id.id)  # Called when printing the receipt in JS

        integrity_check = next(filter(lambda r: r['series_at_code'] == order1.config_id.l10n_pt_pos_at_series_line_id._get_at_code(),
                                      self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertEqual(integrity_check['msg_cover'], 'Orders are correctly hashed')
        self.assertEqual(integrity_check['first_date'], order1.date_order)
        self.assertEqual(integrity_check['last_date'], order4.date_order)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of pos.order to do so.
        Model.write(order3, {'date_order': fields.Date.from_string('2024-01-07')})
        integrity_check = next(filter(lambda r: r['series_at_code'] == order1.config_id.l10n_pt_pos_at_series_line_id._get_at_code(),
                                      self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on POS order with id {order3.id} ({order3.l10n_pt_document_number}).')

        # Let's try with the l10n_pt_pos_inalterable_hash field itself
        Model.write(order3, {'date_order': fields.Date.from_string("2024-01-03")})  # Revert the previous change
        Model.write(order4, {'l10n_pt_pos_inalterable_hash': 'fake_hash'})
        integrity_check = next(filter(lambda r: r['series_at_code'] == order1.config_id.l10n_pt_pos_at_series_line_id._get_at_code(),
                                      self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on POS order with id {order4.id} ({order4.l10n_pt_document_number}).')


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
            'l10n_pt_pos_default_at_series_id': False,
        })
        self.config.write({'payment_method_ids': [Command.link(pos_payment_method.id)]})
        with self.assertRaisesRegex(RedirectWarning, "a payment mechanism. Payment methods with a bank journal"):
            self.open_new_session()
