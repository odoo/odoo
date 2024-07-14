# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import Form, tagged, loaded_demo_data
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):
    def setUp(self):
        super().setUp()
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
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_tln_gtn8
            move.product_uom_qty = 20

        receipt = picking_form.save()
        receipt.action_confirm()
        receipt.action_assign()

        url = self._get_client_action_url(receipt.id).replace('?', '?debug=assets&')
        self.start_tour(url, 'test_gs1_receipt_expiration_date', login='admin', timeout=180)

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(len(receipt.move_line_ids), 3)
        self.assertEqual(
            receipt.move_line_ids.mapped(lambda ml: ml.expiration_date.date().isoformat()),
            ['2022-05-20', '2022-05-21', '2022-05-22']
        )
        self.assertEqual(
            receipt.move_line_ids.lot_id.mapped('name'),
            ['b1-b001', 'b1-b002', 'b1-b003']
        )
        self.assertEqual(
            receipt.move_line_ids.mapped('qty_done'),
            [8, 4, 8]
        )
