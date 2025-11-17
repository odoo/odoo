import logging
from base64 import b64encode

from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from odoo.addons.account_peppol.tests.test_peppol_messages import TestPeppolMessage

_logger = logging.getLogger(__name__)

FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']


@tagged("-at_install", "post_install")
class TestPeppolOrderIntegration(TestPeppolMessage):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.file_path = "sale_peppol/tests/assets"

        cls.env["ir.config_parameter"].sudo().set_param(
            "account_peppol.edi.mode", "test"
        )

        cls.test_product_a = cls.env["product.product"].create(
            {
                "name": "Test Product A",
                "default_code": "PROD-A-001",
                "type": "consu",
                "list_price": 50.0,
            },
        )

        cls.laptop_product = cls.env["product.product"].create(
            {
                "name": "Laptop Pro X1",
                "default_code": "LAPTOP-PRO-X1",
                "type": "consu",
                "list_price": 100.0,
            },
        )

        cls.mouse_product = cls.env["product.product"].create(
            {
                "name": "Wireless Mouse Pro",
                "default_code": "MOUSE-WIRELESS-PRO",
                "type": "consu",
                "list_price": 30.0,
            },
        )

        cls.service_product = cls.env["product.product"].create(
            {
                "name": "IT Consulting Service",
                "default_code": "SERVICE-IT-CONSULTING",
                "type": "service",
                "list_price": 35.0,
            },
        )

        cls.startup_product = cls.env["product.product"].create(
            {
                "name": "Startup Package Premium",
                "default_code": "STARTUP-PKG-PREMIUM",
                "type": "consu",
                "list_price": 100.0,
            },
        )

    def test_end_to_end_basic_order_processing(self):
        """Test complete workflow from XML document to sale order creation - basic order"""
        cls = self.__class__
        cls.mocked_incoming_invoice_fname = 'encrypted_order'

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        move = self.env['sale.order'].sudo().search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{
            'peppol_order_state': 'done',
        }])

    def test_order_change(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order change request.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'encrypted_order'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()
        order = self.env['sale.order'].sudo().search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertEqual(order.amount_total, 7245.0)

        cls.mocked_incoming_invoice_fname = 'encrypted_order_change'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()
        self.assertEqual(order.amount_total, 4855.0)

    def test_order_cancel(self):
        """ Test complete workflow from XML document to sale order creation and follow up receipt
            of order cancellation request.
        """
        cls = self.__class__

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        cls.mocked_incoming_invoice_fname = 'encrypted_order'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        cls.mocked_incoming_invoice_fname = 'encrypted_order_cancel'
        self.env['account_edi_proxy_client.user'].sudo()._cron_peppol_get_new_documents()

        order = self.env['sale.order'].sudo().search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertEqual(order.state, 'cancel')

    # def test_end_to_end_complex_order_processing(self):
    #     """Test complete workflow with complex multi-line order"""
    #     # Create attachment from complex order XML
    #     attachment = self._create_attachment_from_xml_file('complex_order.xml')

    #     # Process the order
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-002')

    #     order = result['order']

    #     # Verify order basic information
    #     self.assertEqual(order.peppol_order_uuid, 'test-uuid-002')
    #     self.assertEqual(order.peppol_order_state, 'received')
    #     self.assertIn('ORDER-COMPLEX-002', order.origin)

    #     # Verify new partner was created for Global Enterprise Corp
    #     self.assertEqual(order.partner_id.name, 'Global Enterprise Corp')
    #     self.assertEqual(order.partner_id.vat, 'US123456789')
    #     self.assertEqual(order.partner_id.country_id.code, 'US')

    #     # Verify all three order lines were created
    #     self.assertEqual(len(order.order_line), 3)

    #     # Check first line (laptop)
    #     line1 = order.order_line[0]
    #     self.assertEqual(line1.product_id, self.laptop_product)
    #     self.assertEqual(line1.product_uom_qty, 5.0)
    #     self.assertEqual(line1.price_unit, 100.0)

    #     # Check second line (mouse)
    #     line2 = order.order_line[1]
    #     self.assertEqual(line2.product_id, self.mouse_product)
    #     self.assertEqual(line2.product_uom_qty, 10.0)
    #     self.assertEqual(line2.price_unit, 30.0)

    #     # Check third line (service)
    #     line3 = order.order_line[2]
    #     self.assertEqual(line3.product_id, self.service_product)
    #     self.assertEqual(line3.product_uom_qty, 20.0)
    #     self.assertEqual(line3.price_unit, 35.0)

    # def test_end_to_end_new_customer_order_processing(self):
    #     """Test complete workflow with new customer creation"""
    #     # Create attachment from new customer order XML
    #     attachment = self._create_attachment_from_xml_file('new_customer_order.xml')

    #     # Process the order
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-003')

    #     order = result['order']

    #     # Verify new partner was created
    #     partner = order.partner_id
    #     self.assertEqual(partner.name, 'Fresh Start Industries')
    #     self.assertEqual(partner.vat, 'NL999888777B01')
    #     self.assertEqual(partner.street, '999 Innovation Drive')
    #     self.assertEqual(partner.city, 'Amsterdam')
    #     self.assertEqual(partner.zip, '1012 AB')
    #     self.assertEqual(partner.country_id.code, 'NL')
    #     self.assertEqual(partner.email, 'e.vandenberg@freshstart.nl')
    #     self.assertEqual(partner.phone, '+31 20 123 4567')
    #     self.assertTrue(partner.is_company)
    #     self.assertEqual(partner.customer_rank, 1)

    #     # Verify order was created
    #     self.assertEqual(order.peppol_order_uuid, 'test-uuid-003')
    #     self.assertEqual(order.peppol_order_state, 'received')
    #     self.assertIn('ORDER-NEW-CUSTOMER-003', order.origin)

    # def test_end_to_end_unmapped_products_order_processing(self):
    #     """Test complete workflow with unmapped products"""
    #     # Create attachment from unmapped products order XML
    #     attachment = self._create_attachment_from_xml_file('unmapped_products_order.xml')

    #     # Process the order
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-004')

    #     order = result['order']

    #     # Verify order was created with existing partner
    #     self.assertEqual(order.partner_id, self.existing_partner)
    #     self.assertEqual(order.peppol_order_uuid, 'test-uuid-004')
    #     self.assertEqual(order.peppol_order_state, 'received')

    #     # Verify order lines were created with warnings for unmapped products
    #     self.assertEqual(len(order.order_line), 2)

    #     # Check first line (unmapped product)
    #     line1 = order.order_line[0]
    #     self.assertFalse(line1.product_id)  # No product mapped
    #     self.assertEqual(line1.product_uom_qty, 1.0)
    #     self.assertEqual(line1.price_unit, 150.0)
    #     self.assertIn('Non-existent product', line1.name)
    #     self.assertIn('Product not found', line1.name)  # Warning message

    #     # Check second line (another unmapped product)
    #     line2 = order.order_line[1]
    #     self.assertFalse(line2.product_id)  # No product mapped
    #     self.assertEqual(line2.product_uom_qty, 2.0)
    #     self.assertEqual(line2.price_unit, 25.0)
    #     self.assertIn('Another product', line2.name)
    #     self.assertIn('Product not found', line2.name)  # Warning message

    # def test_end_to_end_invalid_order_processing(self):
    #     """Test handling of invalid order with missing required fields"""
    #     # Create attachment from invalid order XML
    #     attachment = self._create_attachment_from_xml_file('invalid_order.xml')

    #     # Process the order - should handle gracefully
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-005')

    #     order = result['order']

    #     # Verify order was created but may have default values
    #     self.assertEqual(order.peppol_order_uuid, 'test-uuid-005')
    #     self.assertEqual(order.peppol_order_state, 'received')

    #     # Order should be created with default partner due to missing customer info
    #     self.assertIsNotNone(order.partner_id)

    # def test_end_to_end_malformed_xml_error_handling(self):
    #     """Test error handling for malformed XML"""
    #     # Create attachment with malformed XML content
    #     malformed_xml = b'<Order><unclosed_tag>malformed</Order>'
    #     attachment = self.env['ir.attachment'].create({
    #         'name': 'malformed_order.xml',
    #         'type': 'binary',
    #         'datas': b64encode(malformed_xml),
    #         'mimetype': 'application/xml',
    #     })

    #     # Process the order - should handle error gracefully
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-error')

    #     order = result['order']

    #     # Verify error order was created
    #     self.assertEqual(order.peppol_order_uuid, 'test-uuid-error')
    #     self.assertEqual(order.peppol_order_state, 'error')
    #     self.assertIn('Error', order.origin)
    #     self.assertIsNotNone(order.note)  # Should contain error message

    #     # Verify attachment is linked to error order
    #     self.assertEqual(attachment.res_model, 'sale.order')
    #     self.assertEqual(attachment.res_id, order.id)

    #     # Verify error message was logged
    #     messages = order.message_ids
    #     self.assertTrue(any('Error processing' in msg.body for msg in messages))

    # def test_order_totals_and_currency_handling(self):
    #     """Test that order totals and currency are handled correctly"""
    #     # Create attachment from basic order XML (EUR currency)
    #     attachment = self._create_attachment_from_xml_file('basic_order.xml')

    #     # Process the order
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-totals')

    #     order = result['order']

    #     # Verify currency handling (should use company currency or order currency)
    #     # Note: Actual currency conversion would depend on UBL import mechanism
    #     self.assertIsNotNone(order.currency_id)

    #     # Verify order line totals
    #     line = order.order_line[0]
    #     expected_total = line.product_uom_qty * line.price_unit
    #     self.assertEqual(expected_total, 100.0)  # 2 * 50.0

    # def test_data_integrity_verification(self):
    #     """Test that all data is correctly transferred from XML to sale order"""
    #     # Create attachment from complex order XML
    #     attachment = self._create_attachment_from_xml_file('complex_order.xml')

    #     # Process the order
    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-integrity')

    #     order = result['order']

    #     # Verify partner data integrity
    #     partner = order.partner_id
    #     self.assertEqual(partner.name, 'Global Enterprise Corp')
    #     self.assertEqual(partner.vat, 'US123456789')
    #     self.assertEqual(partner.street, '789 Corporate Blvd')
    #     self.assertEqual(partner.city, 'New York')
    #     self.assertEqual(partner.zip, '10001')
    #     self.assertEqual(partner.country_id.code, 'US')
    #     self.assertEqual(partner.email, 'm.johnson@globalenterprise.com')
    #     self.assertEqual(partner.phone, '+1 212 555 0123')

    #     # Verify order line data integrity
    #     lines = order.order_line
    #     self.assertEqual(len(lines), 3)

    #     # Verify each line has correct data
    #     line_data = [
    #         ('LAPTOP-PRO-X1', 'Laptop Pro X1', 5.0, 100.0),
    #         ('MOUSE-WIRELESS-PRO', 'Wireless Mouse Pro', 10.0, 30.0),
    #         ('SERVICE-IT-CONSULTING', 'IT Consulting Service', 20.0, 35.0),
    #     ]

    #     for i, (code, name, qty, price) in enumerate(line_data):
    #         line = lines[i]
    #         self.assertEqual(line.product_id.default_code, code)
    #         self.assertEqual(line.product_id.name, name)
    #         self.assertEqual(line.product_uom_qty, qty)
    #         self.assertEqual(line.price_unit, price)

    # def test_error_scenarios_and_exception_handling(self):
    #     """Test various error scenarios and their handling"""

    #     # Test 1: Empty attachment
    #     empty_attachment = self.env['ir.attachment'].create({
    #         'name': 'empty.xml',
    #         'type': 'binary',
    #         'datas': b64encode(b''),
    #         'mimetype': 'application/xml',
    #     })

    #     result = self.proxy_user._peppol_import_order(empty_attachment, 'received', 'test-uuid-empty')
    #     order = result['order']
    #     self.assertEqual(order.peppol_order_state, 'error')

    #     # Test 2: Non-XML content
    #     non_xml_attachment = self.env['ir.attachment'].create({
    #         'name': 'not_xml.xml',
    #         'type': 'binary',
    #         'datas': b64encode(b'This is not XML content'),
    #         'mimetype': 'application/xml',
    #     })

    #     result = self.proxy_user._peppol_import_order(non_xml_attachment, 'received', 'test-uuid-nonxml')
    #     order = result['order']
    #     self.assertEqual(order.peppol_order_state, 'error')

    # @patch('odoo.addons.sale_peppol.models.account_edi_proxy_user.Account_Edi_Proxy_ClientUser._create_basic_order_from_data')
    # def test_fallback_to_basic_order_creation(self, mock_create_basic):
    #     """Test fallback to basic order creation when UBL import fails"""
    #     # Mock the UBL import to fail
    #     with patch.object(self.env['sale.order'], '_extend_with_attachments', side_effect=Exception('UBL import failed')):
    #         attachment = self._create_attachment_from_xml_file('basic_order.xml')

    #         result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-fallback')

    #         order = result['order']

    #         # Verify fallback was called
    #         mock_create_basic.assert_called_once()

    #         # Verify order was still created
    #         self.assertEqual(order.peppol_order_uuid, 'test-uuid-fallback')
    #         self.assertEqual(order.peppol_order_state, 'received')

    # def test_concurrent_order_processing(self):
    #     """Test processing multiple orders concurrently"""
    #     # Create multiple attachments
    #     attachments = []
    #     for i in range(3):
    #         attachment = self._create_attachment_from_xml_file('basic_order.xml')
    #         attachments.append(attachment)

    #     # Process orders
    #     results = []
    #     for i, attachment in enumerate(attachments):
    #         result = self.proxy_user._peppol_import_order(attachment, 'received', f'test-uuid-concurrent-{i}')
    #         results.append(result)

    #     # Verify all orders were created
    #     self.assertEqual(len(results), 3)

    #     for i, result in enumerate(results):
    #         order = result['order']
    #         self.assertEqual(order.peppol_order_uuid, f'test-uuid-concurrent-{i}')
    #         self.assertEqual(order.peppol_order_state, 'received')
    #         self.assertEqual(order.partner_id, self.existing_partner)

    # def test_large_order_processing(self):
    #     """Test processing order with many line items"""
    #     # Use complex order which has multiple lines
    #     attachment = self._create_attachment_from_xml_file('complex_order.xml')

    #     result = self.proxy_user._peppol_import_order(attachment, 'received', 'test-uuid-large')

    #     order = result['order']

    #     # Verify all lines were processed
    #     self.assertEqual(len(order.order_line), 3)

    #     # Verify order totals are reasonable
    #     total_qty = sum(line.product_uom_qty for line in order.order_line)
    #     self.assertEqual(total_qty, 35.0)  # 5 + 10 + 20

    #     total_amount = sum(line.product_uom_qty * line.price_unit for line in order.order_line)
    #     self.assertEqual(total_amount, 1500.0)  # 500 + 300 + 700
