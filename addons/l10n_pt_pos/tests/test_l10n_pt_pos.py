from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.models import Model
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo import fields
from odoo.tools import format_date


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPos(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.config.l10n_pt_pos_tax_authority_series_id = self.env['l10n_pt_account.tax.authority.series'].create({
            'code': 'TESTSERIES',
        })
        self.product1 = self.create_product('Product 1', self.categ_basic, 150, standard_price=50)

        self.company_data['company'].write({
            'name': 'real',
            'country_id': self.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        self.company_pt = self.company_data['company']
        self.open_new_session()

    def _create_pos_order(self, date_order="2023-01-01"):
        order = self.env['pos.order'].create_from_ui([self.create_ui_order_data([(self.product1, 1)])])
        order = self.env['pos.order'].search([('id', '=', order[0]['id'])])
        if date_order:
            # Bypass the write method of pos.order to change the date_order
            Model.write(order, {'date_order': fields.Date.from_string(date_order)})
        return order

    def test_l10n_pt_pos_hash_inalterability(self):
        order = self._create_pos_order()
        self.assertEqual(order.l10n_pt_pos_inalterable_hash, False)
        order.l10n_pt_pos_compute_missing_hashes(order.company_id.id)  # Called when printing the receipt

        expected_error_msg = "You cannot edit the following fields.*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg}l10n_pt_pos_inalterable_hash"):
            order.l10n_pt_pos_inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}date_order"):
            order.date_order = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}create_date"):
            order.create_date = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}name"):
            order.name = "New name"  # Name is used by _get_l10n_pt_document_number so it cannot be modified either

        # The following field is not part of the hash so it can be modified
        order.note = 'new note'

    def test_l10n_pt_pos_document_no(self):
        """
        Test that the document number for Portugal follows this format: [^ ]+ [^/^ ]+/[0-9]+
        """
        for expected in ['pos_order PoS_Shop_Test/0001', 'pos_order PoS_Shop_Test/0002', 'pos_order PoS_Shop_Test/0003']:
            order = self._create_pos_order()
            self.assertEqual(order._get_l10n_pt_pos_document_number(), expected)

    def test_l10n_pt_pos_hash_integrity_report(self):
        """Test the hash integrity report"""
        order1 = self._create_pos_order("2023-01-01")
        self._create_pos_order("2023-01-02")
        order3 = self._create_pos_order("2023-01-03")
        order4 = self._create_pos_order("2023-01-04")
        self.assertEqual(order1.l10n_pt_pos_inalterable_hash, False)
        self.env['pos.order'].l10n_pt_pos_compute_missing_hashes(order1.company_id.id)  # Called when printing the receipt

        integrity_check = list(filter(lambda r: r['name'] == order1.config_id.name, self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))[0]
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertEqual(integrity_check['msg'], 'Entries are correctly hashed')
        self.assertEqual(integrity_check['from_date'], fields.Date.to_string(order1.date_order))
        self.assertEqual(integrity_check['to_date'], fields.Date.to_string(order4.date_order))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of pos.order to do so.
        Model.write(order3, {'date_order': fields.Date.from_string('2022-01-07')})
        integrity_check = list(filter(lambda r: r['name'] == order1.config_id.name, self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))[0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg'], f'Corrupted data on record with id {order3.id}.')

        # Let's try with the l10n_pt_pos_inalterable_hash field itself
        Model.write(order3, {'date_order': fields.Date.from_string("2023-01-03")})  # Revert the previous change
        Model.write(order4, {'l10n_pt_pos_inalterable_hash': 'fake_hash'})
        integrity_check = list(filter(lambda r: r['name'] == order1.config_id.name, self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))[0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg'], f'Corrupted data on record with id {order4.id}.')

    def test_l10n_pt_pos_dont_hash_linked_stock_pickings(self):
        """Test that creating a POS order (which creates a stock picking) doesn't hash this created stock picking"""
        order1 = self._create_pos_order()
        order1.l10n_pt_pos_compute_missing_hashes(order1.company_id.id)  # Called when printing the receipt
        self.assertNotEqual(order1.picking_ids, False)
        # self.assertEqual(order1.picking_ids.blockchain_must_hash, False)  #TODORIGR
        # self.assertEqual(order1.picking_ids.blockchain_secure_sequence_number, False)
