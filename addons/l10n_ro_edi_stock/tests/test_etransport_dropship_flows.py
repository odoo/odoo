import unittest
from unittest.mock import patch
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.l10n_ro_edi_stock.tests.common import TestL10nRoEdiStockCommon


@patch('odoo.addons.l10n_ro_edi_stock.models.etransport_api.ETransportAPI._make_etransport_request')
@tagged("post_install_l10n", "post_install", "-at_install")
class TestETransportDropshipFlows(TestL10nRoEdiStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module']._get('stock_dropshipping').state != 'installed':
            raise unittest.SkipTest("stock_dropshipping not installed")
        cls.startClassPatcher(freeze_time('2025-01-14'))

        company = cls.company_data['company']
        company.write({
            'vat': '9000123456789',
            'street': 'Calea Nationala 85',
            'city': 'Botosani',
            'zip': '710052',
            'state_id': cls.env.ref('base.RO_BT').id,
            'l10n_ro_edi_access_token': 'some access token',
        })

        cls.env['res.company'].sudo().create_missing_dropship_picking_type()
        cls.dropship_picking_type = cls.env['stock.picking.type'].search([
            ('code', '=', 'dropship'),
            ('company_id', '=', company.id),
        ], limit=1)

        cls.carrier = cls.env.ref('delivery.free_delivery_carrier')
        cls.product_a.weight = 1

        if 'intrastat_code_id' in cls.env['product.product']._fields:
            cls.default_intrastat_code = cls.env.ref('account_intrastat.commodity_code_2018_1012100')
            cls.product_a.intrastat_code_id = cls.default_intrastat_code

        cls.shipping_partner = cls.env['res.partner'].create({
            'name': 'RO Shipping Partner',
            'vat': '8001011234567',
            'street': 'Strada Mihai Viteazul 22',
            'city': 'Caransebes',
            'zip': '325400',
            'state_id': cls.env.ref('base.RO_CS').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.customer = cls.env['res.partner'].create({
            'name': 'RO Customer',
            'is_company': True,
            'vat': 'RO1234567897',
            'street': 'Strada General Traian Moșoiu 24',
            'city': 'Bran',
            'zip': '507025',
            'state_id': cls.env.ref('base.RO_BV').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.vendor_ro = cls.env['res.partner'].create({
            'name': 'RO Vendor',
            'is_company': True,
            'vat': 'RO1234567897',
            'street': 'Strada Republicii 10',
            'city': 'Cluj-Napoca',
            'zip': '400001',
            'state_id': cls.env.ref('base.RO_CJ').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.vendor_foreign = cls.env['res.partner'].create({
            'name': 'Foreign Vendor',
            'is_company': True,
            'vat': 'DE123456788',
            'street': 'Hauptstrasse 1',
            'city': 'Berlin',
            'zip': '10115',
            'country_id': cls.env.ref('base.de').id,
        })

        cls.customer_b2c = cls.env['res.partner'].create({
            'name': 'RO B2C Customer',
            'is_company': False,
            'street': 'Strada Avram Iancu 5',
            'city': 'Brasov',
            'zip': '500025',
            'state_id': cls.env.ref('base.RO_BV').id,
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.successful_upload_response = {
            'content': {
                "dateResponse": "202212231132",
                "ExecutionStatus": 0,
                "index_incarcare": 1,
                "UIT": "A0002",
                "trace_id": "96cd587e-298b-4245-ad7d-2607d973f9d4",
                "ref_declarant": "",
                "atentie": "Verificati starea XML-ului transmis. Codul UIT este valabil din momentul in care apare ca valid dupa apelul de stare",
            }
        }

    @classmethod
    def _create_dropship_picking(cls, vendor, customer):
        po = cls.env['purchase.order'].create({'partner_id': vendor.id})  # noqa: OLS03001
        po_line = cls.env['purchase.order.line'].create({  # noqa: OLS03001
            'order_id': po.id,
            'product_id': cls.product_a.id,
            'product_qty': 10.0,
            'price_unit': 100.0,
        })
        picking = cls.create_stock_picking(
            partner=customer,
            picking_type=cls.dropship_picking_type,
            product_data=[{
                'product_id': cls.product_a,
                'product_uom_qty': 10.0,
                'quantity': 10.0,
            }],
        )
        picking.move_ids.write({
            'purchase_line_id': po_line.id,
            'partner_id': customer.id,
        })
        return picking

    def test_dropship_domestic_vendor_b2c(self, make_request):
        """
            Scenario : Romanian Supplier -> Romanian B2C Customer.
            The dropshipper performs the declaration for the RO B2C customer (Operation 30 - National transport).
            Expected result: e-Transport XML is generated with company CUI as codDeclarant.
        """
        picking = self._create_dropship_picking(self.vendor_ro, self.customer_b2c)
        picking.carrier_id = self.carrier
        picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        picking.button_validate()

        picking.write({
            'l10n_ro_edi_stock_operation_type': '30',
            'l10n_ro_edi_stock_operation_scope': '705',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
        })

        make_request.return_value = self.successful_upload_response
        picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(picking.l10n_ro_edi_stock_document_ids, 'test_dropship_domestic_vendor_b2c_1')

    def test_dropship_foreign_vendor_b2c(self, make_request):
        """
            Scenario: Foreign Supplier (EU/Non-EU) -> Romanian B2C Customer.
            The dropshipper performs the declaration for the RO B2C customer (Operation 10 - Intra-community purchase).
            Expected result: e-Transport XML is generated with Border Crossing Point (bcp) as loading point.
        """
        picking = self._create_dropship_picking(self.vendor_foreign, self.customer_b2c)
        picking.carrier_id = self.carrier
        picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        picking.button_validate()

        picking.write({
            'l10n_ro_edi_stock_operation_type': '10',
            'l10n_ro_edi_stock_operation_scope': '201',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
            'l10n_ro_edi_stock_start_loc_type': 'bcp',
            'l10n_ro_edi_stock_start_bcp': '3',
        })

        make_request.return_value = self.successful_upload_response
        picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(picking, 'stock_sent', 1, ('enable', 'enable_fetch', 'fields_readonly'))
        self._assert_etransport_document(picking.l10n_ro_edi_stock_document_ids, 'test_dropship_foreign_vendor_b2c_1')

    def test_dropship_domestic_vendor_b2b_error(self, make_request):
        """
            Scenario (Domestic B2B): Romanian Supplier -> Romanian B2B Customer.
            The supplier is responsible for the declaration, so sending from the dropshipper is not required.
            Expected result: Sending fails with an error indicating declaration on behalf of supplier is not required.
        """
        picking = self._create_dropship_picking(self.vendor_ro, self.customer)
        picking.carrier_id = self.carrier
        picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        picking.button_validate()

        picking.write({
            'l10n_ro_edi_stock_operation_type': '30',
            'l10n_ro_edi_stock_operation_scope': '705',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
        })
        picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(picking, 'stock_sending_failed', 1, ('enable', 'enable_send'))
        self.assertIn("Declaration on behalf of the supplier is not required for domestic dropshipping", picking.l10n_ro_edi_stock_document_ids.message)

    def test_dropship_foreign_vendor_b2b_error(self, make_request):
        """
            Scenario: Foreign Supplier -> Romanian B2B Customer.
            Declaration on behalf of another registered Romanian B2B customer is not supported.
            Expected result: Sending fails with an error stating declaration in the name of other registered RO B2B customers is not supported.
        """
        picking = self._create_dropship_picking(self.vendor_foreign, self.customer)
        picking.carrier_id = self.carrier
        picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner
        picking.button_validate()
        picking.write({
            'l10n_ro_edi_stock_operation_type': '10',
            'l10n_ro_edi_stock_operation_scope': '201',
            'l10n_ro_edi_stock_vehicle_number': 'BN18CTL',
            'l10n_ro_edi_stock_start_loc_type': 'bcp',
            'l10n_ro_edi_stock_start_bcp': '3',
        })

        picking.action_l10n_ro_edi_stock_send_etransport()
        self._assert_picking_state(picking, 'stock_sending_failed', 1, ('enable', 'enable_send'))
        self.assertIn("Declaration in the name of other registered Romanian B2B Customers is not supported", picking.l10n_ro_edi_stock_document_ids.message)
