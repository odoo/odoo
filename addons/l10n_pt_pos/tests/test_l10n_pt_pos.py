from unittest.mock import patch

from odoo import fields
from odoo.models import Model
from odoo.tests import tagged
from odoo.exceptions import UserError

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtPos(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.company_data['company'].write({
            'name': 'real',
            'country_id': self.env.ref('base.pt').id,
            'account_fiscal_country_id': self.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        self.company_pt = self.company_data['company']

        self.config = self.basic_config
        self.config.l10n_pt_pos_at_series_id = self.env['l10n_pt.at.series'].create({
            'type': 'pos_order',
            'prefix': 'POS-TEST',
            'at_code': 'AT-POS-TEST',
        })

        self.product1 = self.create_product('Product 1', self.categ_basic, 150, standard_price=50)

        def _patched_l10n_pt_pos_verify_config(*args, **kwargs):
            pass

        with patch('odoo.addons.l10n_pt_pos.models.pos_config.PosConfig._l10n_pt_pos_verify_config', new=_patched_l10n_pt_pos_verify_config):
            self.open_new_session()

    def _create_pos_order(self, date_order="2024-01-01"):
        order_data = self.create_ui_order_data(
            pos_order_lines_ui_args=[
                (self.product1, 1.0),
            ],
            payments=[(self.bank_pm1, 150.0)],
        )
        results = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(results['pos.order'][0]['id'])
        order.action_pos_order_paid()
        if date_order:
            # Bypass the write method of pos.order to change the date_order
            Model.write(order, {'date_order': fields.Date.from_string(date_order)})
        return order

    def test_l10n_pt_pos_hash_inalterability(self):
        order = self._create_pos_order()
        self.assertEqual(order.l10n_pt_pos_inalterable_hash, False)
        order.l10n_pt_pos_compute_missing_hashes(order.company_id.id)  # Called when printing the receipt

        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:.*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Inalterability Hash."):
            order.l10n_pt_pos_inalterable_hash = 'fake_hash'
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Date."):
            order.date_order = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Created on."):
            order.create_date = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, f"{expected_error_msg}Order Ref."):
            order.name = "New name"

        # The following field is not part of the hash so it can be modified
        order.note = 'new note'

    def test_l10n_pt_pos_hash_integrity_report(self):
        """Test the hash integrity report"""
        order1 = self._create_pos_order("2024-01-01")
        self._create_pos_order("2024-01-02")
        order3 = self._create_pos_order("2024-01-03")
        order4 = self._create_pos_order("2024-01-04")
        self.assertEqual(order1.l10n_pt_pos_inalterable_hash, False)
        order1.l10n_pt_pos_compute_missing_hashes(order1.company_id.id)  # Called when printing the receipt in JS

        integrity_check = next(filter(lambda r: r['config_at_code'] == order1.config_id.l10n_pt_pos_at_series_id._get_at_code(), self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertEqual(integrity_check['msg_cover'], 'Orders are correctly hashed')
        self.assertEqual(integrity_check['first_date'], order1.date_order)
        self.assertEqual(integrity_check['last_date'], order4.date_order)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of pos.order to do so.
        Model.write(order3, {'date_order': fields.Date.from_string('2024-01-07')})
        integrity_check = next(filter(lambda r: r['config_at_code'] == order1.config_id.l10n_pt_pos_at_series_id._get_at_code(), self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on POS order with id {order3.id} ({order3.name}).')

        # Let's try with the l10n_pt_pos_inalterable_hash field itself
        Model.write(order3, {'date_order': fields.Date.from_string("2024-01-03")})  # Revert the previous change
        Model.write(order4, {'l10n_pt_pos_inalterable_hash': 'fake_hash'})
        integrity_check = next(filter(lambda r: r['config_at_code'] == order1.config_id.l10n_pt_pos_at_series_id._get_at_code(), self.company_pt._l10n_pt_pos_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on POS order with id {order4.id} ({order4.name}).')
