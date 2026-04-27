from unittest.mock import patch

from freezegun import freeze_time
from odoo.addons.l10n_uy_edi.tests.common import TestUyEdi
from odoo.tests.common import tagged
from odoo.tools import misc

from odoo import Command


@tagged("-at_install", "post_install", "post_install_l10n")
class TestUyEdiStock(TestUyEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create warehouse for delivery guides
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)])

        # Create stock locations
        cls.stock_location = cls.env['stock.location'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('usage', '=', 'internal')
        ], limit=1)

        cls.customer_location = cls.env.ref('stock.stock_location_customers', raise_if_not_found=False)

        # Create picking type for outgoing
        cls.picking_type_out = cls.env['stock.picking.type'].create({
            'name': 'Delivery Orders Test',
            'code': 'outgoing',
            'sequence_code': 'OUT_TEST',
            'warehouse_id': cls.warehouse.id,
            'default_location_src_id': cls.stock_location.id,
            'default_location_dest_id': cls.customer_location.id,
        })

        # Create products for stock moves
        cls.product_delivery = cls.env["product.product"].create({
            "name": "Test delivery product",
            "list_price": 100.0
        })

        # Create document type for delivery guide
        cls.document_type_delivery = cls.env.ref("l10n_uy.dc_e_remito")
        cls.mocked_responses_path = "l10n_uy_edi_stock/tests/responses/"
        cls.mocked_cfes_path = "l10n_uy_edi_stock/tests/expected_cfes/"

    @classmethod
    def _create_stock_picking(cls, **kwargs):
        """Create a stock picking for delivery guide testing"""
        with freeze_time(cls.frozen_today, tz_offset=3):
            picking = cls.env['stock.picking'].create({
                'partner_id': cls.partner_local.id,
                'picking_type_id': cls.picking_type_out.id,
                'location_id': cls.stock_location.id,
                'location_dest_id': cls.customer_location.id,
                'l10n_latam_document_type_id': cls.document_type_delivery.id,
                'l10n_uy_edi_operation_type': '1',  # Sale
                'move_ids': cls._get_stock_picking_move_line_vals(cls),
                **kwargs
            })

            # Confirm and assign the picking
            picking.action_confirm()
            picking.action_assign()

        return picking

    def _get_stock_picking_move_line_vals(self):
        '''
        Default values for creating stock picking move lines
        '''
        return [Command.create({
            'product_id': self.product_delivery.id,
            'name': '[PROD_DEL] Test delivery product',
            'product_uom_qty': 1.0,
            'product_uom': self.product_delivery.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })]

    def _validate_and_create_delivery_guide(self, picking):
        """Validate picking and create delivery guide"""
        # Mark as done
        picking.button_validate()

        # Create delivery guide
        picking.l10n_uy_edi_create_delivery_guide()
        return picking

    def _mock_create_delivery_guide(self, picking, expected_xml_file, exception=None, get_pdf=False):
        """Mock the delivery guide creation process"""
        inbox_patch = dict(
            target=f"{self.utils_path}._ucfe_inbox",
            return_value=self._mocked_response(expected_xml_file, exception=exception),
        )
        query_patch = dict(
            target=f"{self.utils_path}._ucfe_query",
            return_value=self._mocked_response(expected_xml_file + "_pdf" if get_pdf else False),
        )
        with patch(**inbox_patch), patch(**query_patch):
            picking.l10n_uy_edi_create_delivery_guide()

    def _check_cfe(self, picking, expected_xml_file):
        self.assertEqual(picking.l10n_uy_edi_cfe_state, "accepted", "CFE not accepted in demo mode not possible (it is always accepted)")
        expected_xml = self.get_xml_tree_from_string(misc.file_open(self.mocked_cfes_path + expected_xml_file + ".xml").read())
        result_xml = self.get_xml_tree_from_attachment(picking.l10n_uy_edi_document_id.attachment_id)

        # For delivery guides with reference we need to change the original expected document to add the proper tag.
        ref_number = False
        if picking.l10n_uy_edi_reference:
            ref_number = picking.l10n_uy_edi_document_id._get_doc_parts(picking.l10n_uy_edi_reference)[1]
        if ref_number:
            namespace = {"cfe": "http://cfe.dgi.gub.uy"}
            expected_xml.find(".//cfe:Referencia/cfe:Referencia/cfe:NroCFERef", namespace).text = ref_number
        else:
            self.assertXmlTreeEqual(expected_xml, result_xml)
