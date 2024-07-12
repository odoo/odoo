import freezegun
from unittest.mock import patch

from odoo import fields
from odoo.models import Model
from odoo.tests import tagged
from odoo.exceptions import UserError

from odoo.addons.stock.tests.common import TestStockCommon


class TestL10nPtStockCommon(TestStockCommon):
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
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Partner A',
            'vat': 'PT123456789',
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

    def create_picking(self, picking_type, l10n_pt_hashed_on="2023-01-01", partner=False, product=False, validate=False):
        product = product or self.productA
        move_line = self.env['stock.move.line'].create({
            'company_id': self.company_pt.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'quantity': 1,
        })
        picking = self.env['stock.picking'].create({
            'move_type': 'direct',
            'company_id': self.company_pt.id,
            'partner_id': (partner or self.partner_a).id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'picking_type_id': picking_type.id,
            'move_line_ids': move_line,
        })
        self.env['stock.move'].create({
            'company_id': self.company_pt.id,
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 10,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'move_line_ids': move_line,
        })
        if validate:
            with freezegun.freeze_time(l10n_pt_hashed_on):
                picking.with_context(skip_backorder=True).button_validate()
        return picking


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtStockHashing(TestL10nPtStockCommon):
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

        for (l10n_pt_stock_document_number, picking_type, amount, l10n_pt_hashed_on, expected_hash) in [
            ('1G 5A/1', self.picking_type_out, 679.61, '2017-09-15T15:58:01', "fGqopcOBeYlO9s2yVg92WfVZW5S+2UpjLM0w19zt/2ns8YQX1lNGR80XhT89LyP2bc0GZoBWQBXILbKUMtpm6tI8L+DpI+pPbktPAWG3FCy53/b784TNzQEQvklYNV/b6fqeVnoh8eVZ24V/IFuSslIfLKfrys/ymyER9+0tEcY="),
            ('1G 5A/2', self.picking_type_out, 679.61, '2017-11-30T23:10:23', "gtevyKthLaOI53nTrGz91OwpJHv40vYme1/BqL8YXj17K4EziZCkvnZptorl/Jkz571RvLK2tF1QfLLexPqY5WSXaQPGV8WFy7HCPlrg6IOLQuOXIVK6Z1hOAO+LGDC6Efuov6STP39Sd/wYXpclfHGcVA54AvkzDp1UOTyXzsU="),
            ('1G 5A/3', self.picking_type_out, 1487.67, '2017-12-17T08:00:56', "xmVWmhG9fxZOyTGAfX1O+0YaWtLrPh+Z0/EXCiTpmIVuI02MCagrqv30soM8KgDfrpkAGN1WSgJ40LRcfnsHx0ztZx4HfNj8j75UOayI4i1SJVOh6FSb/V3JwwsNh9QIM8/tF0Ba7SKqVavscAezbTNPCoKpbkyJbfICBXR/F0g="),
            (False, self.picking_type_in, 666, '2017-12-17T08:00:56', False)
        ]:
            with (
                patch('odoo.addons.l10n_pt_stock.models.stock_picking.StockPicking._get_l10n_pt_stock_document_number', _get_l10n_pt_stock_document_number_patched),
                patch('odoo.addons.l10n_pt_stock.models.stock_picking.StockPicking._get_l10n_pt_stock_gross_total', _get_l10n_pt_stock_gross_total_patched)
            ):
                with freezegun.freeze_time(l10n_pt_hashed_on):
                    picking = self.create_picking(picking_type, l10n_pt_hashed_on=l10n_pt_hashed_on, validate=True)  # No previous record
                    picking._l10n_pt_stock_compute_missing_hashes()
                    actual_hash = picking.l10n_pt_stock_inalterable_hash.split("$")[2] if picking.l10n_pt_stock_inalterable_hash else picking.l10n_pt_stock_inalterable_hash
                    self.assertEqual(actual_hash, expected_hash)

    def test_l10n_pt_stock_hash_inalterability(self):
        picking = self.create_picking(self.picking_type_out, l10n_pt_hashed_on="2023-01-01", validate=True)
        picking._l10n_pt_stock_compute_missing_hashes()

        expected_error_msg = "This document is protected by a hash. Therefore, you cannot edit the following fields:*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Inalterability Hash."):
            picking.l10n_pt_stock_inalterable_hash = '$1$fake_hash'
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Date of Transfer"):
            picking.date_done = fields.Date.from_string('2000-01-01')
        with self.assertRaisesRegex(UserError, expected_error_msg):
            picking.l10n_pt_hashed_on = fields.Datetime.now()
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Reference."):
            picking.name = "Fake name"  # Name is used by l10n_pt_stock_document_number so it cannot be modified either

        # The following field is not part of the hash so it can be modified
        picking.note = 'new note'

    def test_l10n_pt_stock_hash_integrity_report(self):
        """Test the hash integrity report"""
        picking1 = self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-01', validate=True)
        self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-02', validate=True)
        picking3 = self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-03', validate=True)
        picking4 = self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-04', validate=True)

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


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStockMiscRequirements(TestL10nPtStockCommon):
    def test_l10n_pt_stock_partner(self):
        """Test misc requirements for partner"""

        # Cannot change tax number of an existing client with already issued documents.
        # However, missing tax number can only be entered if the field is empty
        # (or filled with generic client tax 999999990)
        partner_a = self.env['res.partner'].create({
            'name': 'Partner A',
            'company_id': self.company_pt.id,
        })
        partner_a.vat = "PT123456789"
        partner_a.vat = "999999990"

        self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-02', partner=partner_a, validate=True)

        partner_a.vat = "PT123456789"
        with self.assertRaisesRegex(UserError, "You cannot change the VAT number of a partner that already has issued documents"):
            partner_a.vat = "PT987654321"

        # Do not allow change the name of client (if it already has issued docs) who has no tax number.
        # Limitation ends when client has a tax number.

        partner_b = self.env['res.partner'].create({
            'name': 'Partner B',
            'company_id': self.company_pt.id,
        })
        with self.assertRaisesRegex(UserError, "You cannot change the name of a partner without a VAT number"):
            partner_b.name = "Partner B2"

        partner_b.vat = "PT123456789"
        partner_b.name = "Partner B2"

    def test_l10n_pt_stock_product(self):
        """Test that we do not allow change ProductDescription if already issued docs"""

        product = self.env['product.product'].create({
            'name': 'Product A',
            'list_price': 150,
            'taxes_id': [],
        })
        product.name = "Product A2"  # OK

        self.create_picking(self.picking_type_out, l10n_pt_hashed_on='2023-01-02', product=product, validate=True)

        with self.assertRaisesRegex(UserError, "You cannot modify the name of a product that has been used in a stock picking."):
            product.name = "Product A3"
