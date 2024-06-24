import datetime
import freezegun
from unittest.mock import patch

from odoo import fields
from odoo.models import Model
from odoo.tests import tagged
from odoo.exceptions import UserError

from odoo.addons.stock.tests.common import TestStockCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtStock(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_pt = cls.env['res.company'].create({
            'name': 'Company PT',
            'street': '250 Executive Park Blvd, Suite 3400',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'vat': 'PT123456789',
        })
        cls.location = cls.env['stock.location'].create({
            'name': 'Location PT 1',
            'usage': 'internal',
            'company_id': cls.company_pt.id,
        })
        cls.location2 = cls.env['stock.location'].create({
            'name': 'Location PT 2',
            'usage': 'internal',
            'company_id': cls.company_pt.id,
        })
        cls.picking_type_out = cls.env['stock.picking.type'].create({
            'name': 'Picking Out',
            'sequence_code': 'PT_OUT',
            'code': 'outgoing',
            'reservation_method': 'at_confirm',
            'company_id': cls.company_pt.id,
            'warehouse_id': False,
            'default_location_src_id': cls.location.id,
            'default_location_dest_id': cls.location2.id,
        })
        cls.picking_type_in = cls.env['stock.picking.type'].create({
            'name': 'Picking In',
            'sequence_code': 'PT_IN',
            'code': 'incoming',
            'reservation_method': 'at_confirm',
            'company_id': cls.company_pt.id,
            'warehouse_id': False,
            'default_location_src_id': cls.location.id,
            'default_location_dest_id': cls.location2.id,
        })
        for picking_type in cls.env['stock.picking.type'].search([
            ('company_id', '=', cls.company_pt.id),
            ('code', '=', 'outgoing'),
        ]):
            picking_type.l10n_pt_stock_at_series_id = cls.env['l10n_pt.at.series'].create({
                'company_id': cls.company_pt.id,
                'type': 'stock_picking',
                'prefix': f"{picking_type.sequence_code}-TEST",
                'at_code': f"AT-{picking_type.sequence_code}-TEST",
            })

    def create_picking(self, picking_type, date_done="2023-01-01", create_date=None, validate=False):
        move_line = self.env['stock.move.line'].create({
            'company_id': self.company_pt.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'quantity': 1,
        })
        picking = self.env['stock.picking'].create({
            'move_type': 'direct',
            'company_id': self.company_pt.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'picking_type_id': picking_type.id,
            'move_line_ids': move_line,
        })
        self.env['stock.move'].create({
            'company_id': self.company_pt.id,
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'move_line_ids': move_line,
        })
        if validate:
            # Bypass ORM to update the create_date
            create_date = datetime.datetime.strptime(create_date, '%Y-%m-%dT%H:%M:%S') if create_date else date_done
            picking._cr.execute('''
                UPDATE stock_picking
                   SET create_date = %s
                 WHERE id = %s
            ''', (create_date, picking.id))
            picking.invalidate_recordset(['create_date'])
            with freezegun.freeze_time(date_done):
                picking.with_context(skip_backorder=True).button_validate()
        return picking

    def test_l10n_pt_stock_hash_sequence(self):
        """
        Test that the hash sequence is correct.
        For this, we use the following resource provided by the Portuguese tax authority:
        https://info.portaldasfinancas.gov.pt/apps/saft-pt01/local/saft_idemo599999999.xml
        We create stock pickings with the same info as in the link, and we check that the hash that we obtain in Odoo
        is the same as the one given in the link (using the same sample keys).
        """

        # The 1st patch is necessary because we use the move type in l10n_pt_stock_document_number, but our type
        # (stock_picking) is different from the one used in the link (GR)
        # The 2nd is necessary because the example uses a real amount for the computation of the hash,
        # however in our case this amount is set to 0.0, so we need to patch it to get the same result.
        l10n_pt_stock_document_number = ''
        amount = 0.0

        def _get_l10n_pt_stock_document_number_patched(stock_picking):
            return l10n_pt_stock_document_number

        def _get_l10n_pt_stock_gross_total_patched(stock_picking):
            return amount

        for (l10n_pt_stock_document_number, picking_type, amount, date_done, create_date, expected_hash) in [
            ('1G 5A/1', self.picking_type_out, 679.61, '2017-09-15', '2017-09-15T15:58:01', "fGqopcOBeYlO9s2yVg92WfVZW5S+2UpjLM0w19zt/2ns8YQX1lNGR80XhT89LyP2bc0GZoBWQBXILbKUMtpm6tI8L+DpI+pPbktPAWG3FCy53/b784TNzQEQvklYNV/b6fqeVnoh8eVZ24V/IFuSslIfLKfrys/ymyER9+0tEcY="),
            ('1G 5A/2', self.picking_type_out, 679.61, '2017-11-30', '2017-11-30T23:10:23', "gtevyKthLaOI53nTrGz91OwpJHv40vYme1/BqL8YXj17K4EziZCkvnZptorl/Jkz571RvLK2tF1QfLLexPqY5WSXaQPGV8WFy7HCPlrg6IOLQuOXIVK6Z1hOAO+LGDC6Efuov6STP39Sd/wYXpclfHGcVA54AvkzDp1UOTyXzsU="),
            ('1G 5A/3', self.picking_type_out, 1487.67, '2017-12-17', '2017-12-17T08:00:56', "xmVWmhG9fxZOyTGAfX1O+0YaWtLrPh+Z0/EXCiTpmIVuI02MCagrqv30soM8KgDfrpkAGN1WSgJ40LRcfnsHx0ztZx4HfNj8j75UOayI4i1SJVOh6FSb/V3JwwsNh9QIM8/tF0Ba7SKqVavscAezbTNPCoKpbkyJbfICBXR/F0g="),
            (False, self.picking_type_in, 666, '2017-12-17', '2017-12-17T08:00:56', False)
        ]:
            with (
                patch('odoo.addons.l10n_pt_stock.models.stock_picking.StockPicking._get_l10n_pt_stock_document_number', _get_l10n_pt_stock_document_number_patched),
                patch('odoo.addons.l10n_pt_stock.models.stock_picking.StockPicking._get_l10n_pt_stock_gross_total', _get_l10n_pt_stock_gross_total_patched)
            ):
                picking = self.create_picking(picking_type, date_done=date_done, create_date=create_date, validate=True)  # No previous record
                picking._l10n_pt_stock_compute_missing_hashes()
                actual_hash = picking.l10n_pt_stock_inalterable_hash.split("$")[2] if picking.l10n_pt_stock_inalterable_hash else picking.l10n_pt_stock_inalterable_hash
                self.assertEqual(actual_hash, expected_hash)

    def test_l10n_pt_stock_hash_inalterability(self):
        picking = self.create_picking(self.picking_type_out, date_done="2023-01-01", validate=True)
        picking._l10n_pt_stock_compute_missing_hashes()

        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Inalterability Hash."):
            picking.l10n_pt_stock_inalterable_hash = '$1$fake_hash'
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Date of Transfer"):
            picking.date_done = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, expected_error_msg):
            picking.create_date = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Reference."):
            picking.name = "Fake name"  # Name is used by l10n_pt_stock_document_number so it cannot be modified either

        # The following field is not part of the hash so it can be modified
        picking.note = 'new note'

    def test_l10n_pt_stock_hash_integrity_report(self):
        """Test the hash integrity report"""
        picking1 = self.create_picking(self.picking_type_out, date_done='2023-01-01', validate=True)
        self.create_picking(self.picking_type_out, date_done='2023-01-02', validate=True)
        picking3 = self.create_picking(self.picking_type_out, date_done='2023-01-03', validate=True)
        picking4 = self.create_picking(self.picking_type_out, date_done='2023-01-04', validate=True)

        integrity_check = next(filter(lambda r: r['picking_type_at_code'] == self.picking_type_out.l10n_pt_stock_at_series_id._get_at_code(), self.company_pt._l10n_pt_stock_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertRegex(integrity_check['msg_cover'], 'Delivery orders are correctly hashed')
        self.assertEqual(integrity_check['first_date'], picking1.date_done)
        self.assertEqual(integrity_check['last_date'], picking4.date_done)

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of stock.picking to do so.
        Model.write(picking3, {'date_done': fields.Date.from_string('2022-01-07')})
        integrity_check = next(filter(lambda r: r['picking_type_at_code'] == self.picking_type_out.l10n_pt_stock_at_series_id._get_at_code(), self.company_pt._l10n_pt_stock_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on delivery order with id {picking3.id} ({picking3.name}).')

        # Let's try with the l10n_pt_stock_inalterable_hash field itself
        Model.write(picking3, {'date_done': fields.Date.from_string("2023-01-03")})  # Revert the previous change
        Model.write(picking4, {'l10n_pt_stock_inalterable_hash': 'fake_hash'})
        integrity_check = next(filter(lambda r: r['picking_type_at_code'] == self.picking_type_out.l10n_pt_stock_at_series_id._get_at_code(), self.company_pt._l10n_pt_stock_check_hash_integrity()['results']))
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg_cover'], f'Corrupted data on delivery order with id {picking4.id} ({picking4.name}).')
