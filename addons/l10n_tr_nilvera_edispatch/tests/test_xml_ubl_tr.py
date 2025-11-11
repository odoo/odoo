from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdispatchUBLTr(TestUBLTRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'TRW',
            'sequence': 5,
        })

    def test_xml_invoice_with_edispatches(self):
        with freeze_time('2025-03-05'):
            self.eidspatch_ids = self.env['stock.picking'].create([
                {
                    'partner_id': self.einvoice_partner.id,
                    'picking_type_id': self.warehouse_1.out_type_id.id,
                    'location_id': self.warehouse_1.lot_stock_id.id,
                    'move_line_ids': [
                        Command.create({'product_id': self.product_a.id, 'qty_done': qty}),
                    ],
                    'l10n_tr_nilvera_dispatch_state': 'sent',
                } for qty in [1, 2]
            ])
            generated_xml = self._generate_invoice_xml(
                partner_id=self.einvoice_partner,
                l10n_tr_nilvera_edispatch_ids=self.eidspatch_ids.ids
            )

        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/invoice_with_edispatches.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))
