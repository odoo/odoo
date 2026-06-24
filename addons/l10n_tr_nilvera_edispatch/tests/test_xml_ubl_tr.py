from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdispatchUBLTr(TestUBLTRCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'TRW',
            'sequence': 5,
        })
        cls.warehouse_1.out_type_id.sequence_code = "WH/NIL/"

    @classmethod
    def _create_stock_picking(cls, **kwargs):
        with freeze_time('2025-03-05'):
            eidspatch_ids = cls.env['stock.picking'].create({
                'partner_id': cls.einvoice_partner.id,
                'picking_type_id': cls.warehouse_1.out_type_id.id,
                'location_id': cls.warehouse_1.lot_stock_id.id,
                'move_line_ids': [
                    Command.create({'product_id': cls.product_a.id, 'qty_done': 1}),
                ],
                'l10n_tr_nilvera_send_status': 'sent',
                **kwargs,
            })
        return eidspatch_ids

    def test_xml_invoice_with_edispatches(self):
        with freeze_time('2025-03-05'):
            edispatch_ids = self._create_stock_picking()
            generated_xml = self._generate_invoice_xml(
                partner_id=self.einvoice_partner,
                l10n_tr_nilvera_edispatch_ids=edispatch_ids.ids,
            )

        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/invoice_with_edispatches.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_earchive_ecommerce_sale_with_transfer(self):
        with freeze_time('2025-03-05'):
            edispatch_ids = self._create_stock_picking(
                partner_id=self.earchive_partner.id,
                l10n_tr_nilvera_carrier_id=self.einvoice_partner.id,
            )
            invoice = self._generate_invoice(
                partner_id=self.earchive_partner,
                l10n_tr_sales_type='website',
                l10n_tr_nilvera_edispatch_ids=edispatch_ids.ids,
            )
            self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_method_line_id': self.inbound_payment_method_line.id})\
            ._create_payments()
            generated_xml = self.env['account.edi.xml.ubl.tr']._export_invoice(invoice)[0]

        with file_open('l10n_tr_nilvera_edispatch/tests/test_files/invoice_earchive_ecommerce_sale_with_transfer.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))
