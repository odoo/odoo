# -*- coding: utf-8 -*-
import datetime
from unittest.mock import patch

import freezegun

from odoo import fields
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo.models import Model
from odoo.tests import tagged
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStock(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'My Company PT',
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
            'company_id': cls.company.id,
        })
        cls.location2 = cls.env['stock.location'].create({
            'name': 'Location PT 2',
            'usage': 'internal',
            'company_id': cls.company.id,
        })
        cls.l10n_pt_stock_official_series_id = cls.env['l10n_pt_account.official.series'].create({
            'code': 'TESTSERIES',
        })
        cls.picking_type_out = cls.env['stock.picking.type'].create({
            'name': 'Picking Out',
            'sequence_code': 'OUT',
            'code': 'outgoing',
            'reservation_method': 'at_confirm',
            'company_id': cls.company.id,
            'warehouse_id': False,
            'l10n_pt_stock_official_series_id': cls.l10n_pt_stock_official_series_id.id,
        })
        cls.picking_type_in = cls.env['stock.picking.type'].create({
            'name': 'Picking In',
            'sequence_code': 'IN',
            'code': 'incoming',
            'reservation_method': 'at_confirm',
            'company_id': cls.company.id,
            'warehouse_id': False,
        })

    def create_picking(self, picking_type, date_done="2023-01-01", create_date=None, validate=False):
        move_line = self.env['stock.move.line'].create({
            'company_id': self.company.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'qty_done': 1,
        })
        picking = self.env['stock.picking'].create({
            'move_type': 'direct',
            'company_id': self.company.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'picking_type_id': picking_type.id,
            'move_line_ids': move_line,
        })
        self.env['stock.move'].create({
            'company_id': self.company.id,
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'state': 'done',
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
                picking.button_validate()
        return picking

    def test_l10n_pt_stock_hash_sequence(self):
        """
        Test that the hash sequence is correct.
        For this, we use the following resource provided by the Portuguese tax authority:
        https://info.portaldasfinancas.gov.pt/apps/saft-pt01/local/saft_idemo599999999.xml
        We create stock pickings with the same info as in the link, and we check that the hash that we obtain in Odoo
        is the same as the one given in the link (using the same sample keys).
        """

        # The 1st patch is necessary because we use the move type in l10n_pt_stock_document_number, but our
        # move type (outgoing) is different from the one used in the link (GR)
        # The 2nd is necessary because the example uses a real amount for the computation of the hash,
        # however in our case this amount is set to 0.0, so we need to patch it to get the same result.
        l10n_pt_stock_document_number = ''
        amount = 0.0

        def _l10n_pt_stock_get_message_to_hash_patched(stock_order, previous_hash):
            stock_order.ensure_one()
            return L10nPtHashingUtils._l10n_pt_get_message_to_hash(stock_order.date_done, stock_order.create_date, amount, l10n_pt_stock_document_number, previous_hash)

        for (l10n_pt_stock_document_number, picking_type, amount, date_done, create_date, expected_hash) in [
            ('1G 5A/1', self.picking_type_out, 679.61, '2017-09-15', '2017-09-15T15:58:01', "fGqopcOBeYlO9s2yVg92WfVZW5S+2UpjLM0w19zt/2ns8YQX1lNGR80XhT89LyP2bc0GZoBWQBXILbKUMtpm6tI8L+DpI+pPbktPAWG3FCy53/b784TNzQEQvklYNV/b6fqeVnoh8eVZ24V/IFuSslIfLKfrys/ymyER9+0tEcY="),
            ('1G 5A/2', self.picking_type_out, 679.61, '2017-11-30', '2017-11-30T23:10:23', "gtevyKthLaOI53nTrGz91OwpJHv40vYme1/BqL8YXj17K4EziZCkvnZptorl/Jkz571RvLK2tF1QfLLexPqY5WSXaQPGV8WFy7HCPlrg6IOLQuOXIVK6Z1hOAO+LGDC6Efuov6STP39Sd/wYXpclfHGcVA54AvkzDp1UOTyXzsU="),
            ('1G 5A/3', self.picking_type_out, 1487.67, '2017-12-17', '2017-12-17T08:00:56', "xmVWmhG9fxZOyTGAfX1O+0YaWtLrPh+Z0/EXCiTpmIVuI02MCagrqv30soM8KgDfrpkAGN1WSgJ40LRcfnsHx0ztZx4HfNj8j75UOayI4i1SJVOh6FSb/V3JwwsNh9QIM8/tF0Ba7SKqVavscAezbTNPCoKpbkyJbfICBXR/F0g="),
            (False, self.picking_type_in, 666, '2017-12-17', '2017-12-17T08:00:56', False)
        ]:
            with patch('odoo.addons.l10n_pt_stock.models.stock_picking.StockPicking._l10n_pt_stock_get_message_to_hash', _l10n_pt_stock_get_message_to_hash_patched):
                picking = self.create_picking(picking_type, date_done=date_done, create_date=create_date, validate=True)  # No previous record
                actual_hash = picking.l10n_pt_stock_inalterable_hash.split("$")[2] if picking.l10n_pt_stock_inalterable_hash else picking.l10n_pt_stock_inalterable_hash
                self.assertEqual(actual_hash, expected_hash)

    def test_l10n_pt_stock_hash_inalterability(self):
        picking = self.create_picking(self.picking_type_out, date_done="2023-01-01", validate=True)

        expected_error_msg = "You cannot edit the following fields.*"

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

        integrity_check = self.company._l10n_pt_stock_check_hash_integrity()['results'][0]  # [0] = 'out_invoice'
        self.assertEqual(integrity_check['status'], 'verified')
        self.assertRegex(integrity_check['msg'], 'Entries are correctly hashed')
        self.assertEqual(integrity_check['from_date'], fields.Date.to_string(picking1.date_done))
        self.assertEqual(integrity_check['to_date'], fields.Date.to_string(picking4.date_done))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of stock.picking to do so.
        Model.write(picking3, {'date_done': fields.Date.from_string('2022-01-07')})
        integrity_check = self.company._l10n_pt_stock_check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg'], f'Corrupted data on record {picking3.name} with id {picking3.id}.')

        # Let's try with the l10n_pt_stock_inalterable_hash field itself
        Model.write(picking3, {'date_done': fields.Date.from_string("2023-01-03")})  # Revert the previous change
        Model.write(picking4, {'l10n_pt_stock_inalterable_hash': '$1$fake_hash'})
        integrity_check = self.company._l10n_pt_stock_check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['status'], 'corrupted')
        self.assertEqual(integrity_check['msg'], f'Corrupted data on record {picking4.name} with id {picking4.id}.')
