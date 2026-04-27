# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import Form, tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):
    def setUp(self):
        super().setUp()
        self.productlot1.use_expiration_date = True
        self.product_tln_gtn8.write({
            'use_expiration_date': True,
            'expiration_time': 10,
            'use_time': 1,
        })

    def test_gs1_receipt_expiration_date(self):
        """Creates a new receipt and scans barcodes with expiration date and/or
        best before date. When only a best before date is scanned, it will be
        convert to expiration date according to the setting on the product. When
        both dates are scanned, only the expiration date will be used.
        """
        self.env.ref('base.group_user').implied_ids += self.env.ref('stock.group_production_lot')
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_tln_gtn8
            move.product_uom_qty = 25

        receipt = picking_form.save()
        receipt.action_confirm()
        receipt.action_assign()

        self.env.user.groups_id += self.env.ref('product.group_stock_packaging')
        self.env['product.packaging'].create({
            'name': '5 Pack',
            'qty': 5,
            'product_id': self.product_tln_gtn8.id,
            'barcode': '01234567890128',
        })

        url = self._get_client_action_url(receipt.id).replace('?', '?debug=assets&')
        self.start_tour(url, 'test_gs1_receipt_expiration_date', login='admin', timeout=180)

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(len(receipt.move_line_ids), 4)
        self.assertEqual(
            receipt.move_line_ids.mapped(lambda ml: ml.expiration_date.date().isoformat()),
            ['2022-05-20', '2022-05-21', '2022-05-22', '2022-05-24']
        )
        self.assertEqual(
            receipt.move_line_ids.lot_id.mapped('name'),
            ['b1-b001', 'b1-b002', 'b1-b003', 'b1-b004']
        )
        self.assertEqual(
            receipt.move_line_ids.mapped('qty_done'),
            [8, 4, 8, 5]
        )

    def test_delivery_package_with_expiration_dates(self):
        """
        Scan a package with a tracked product that has an expiration date.
        Ensure that the date is displayed on the line
        """
        self.clean_access_rights()
        self.env.user.write({
            'groups_id': [
                (4, self.env.ref('stock.group_tracking_lot').id),
                (4, self.env.ref('stock.group_production_lot').id),
            ],
        })

        lot = self.env['stock.lot'].create({
            'name': 'SuperLot',
            'product_id': self.productlot1.id,
            'expiration_date': '2024-12-31 13:00:00',
        })
        package = self.env['stock.quant.package'].create({
            'name': 'SuperPackage',
        })
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 1, lot_id=lot, package_id=package)

        delivery = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_delivery_package_with_expiration_dates', login='admin')
