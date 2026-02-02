# import logging
# from lxml import etree
# from unittest.mock import patch

# from odoo.tests.common import tagged, TransactionCase
# from odoo.exceptions import UserError
# from odoo.tools.misc import file_open

# _logger = logging.getLogger(__name__)

# FILE_PATH = 'sale_peppol/tests/assets'


# @tagged('-at_install', 'post_install')
# class TestPeppolOrderProcessing(TransactionCase):

#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
        
#         # Set up company with Peppol configuration
#         cls.env.company.write({
#             'country_id': cls.env.ref('base.be').id,
#             'peppol_eas': '0208',
#             'peppol_endpoint': '0477472701',
#             'account_peppol_proxy_state': 'receiver',
#         })
        
#         # Create proxy user for testing
#         cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
#             'id_client': 'test-client-id',
#             'proxy_type': 'peppol',
#             'edi_mode': 'test',
#             'edi_identification': 'test-identification',
#             'company_id': cls.env.company.id,
#         })
        
#         # Create test partners
#         cls.existing_partner = cls.env['res.partner'].create({
#             'name': 'Test Customer Ltd',
#             'vat': 'BE0477472701',
#             'street': '123 Test Street',
#             'city': 'Brussels',
#             'zip': '1000',
#             'country_id': cls.env.ref('base.be').id,
#             'email': 'john.doe@testcustomer.com',
#             'phone': '+32 2 123 4567',
#             'is_company': True,
#             'customer_rank': 1,
#         })
        
#         # Create test products
#         cls.existing_product = cls.env['product.product'].create({
#             'name': 'Test Product A',
#             'default_code': 'PROD-A-001',
#             'type': 'product',
#             'list_price': 50.0,
#         })
        
#         cls.existing_product_by_name = cls.env['product.product'].create({
#             'name': 'Laptop Pro X1',
#             'default_code': 'LAPTOP-001',
#             'type': 'product',
#             'list_price': 100.0,
#         })

#     def _load_xml_file(self, filename):
#         """Load XML file from test assets"""
#         with file_open(f'{FILE_PATH}/{filename}', 'rb') as f:
#             return etree.parse(f)

#     def test_parse_basic_order_xml(self):
#         """Test parsing of basic order XML document"""
#         xml_tree = self._load_xml_file('basic_order.xml')
        
#         order_data = self.proxy_user._parse_peppol_order_xml(xml_tree)
        
#         # Verify basic order information
#         self.assertEqual(order_data['order_number'], 'ORDER-001')
#         self.assertEqual(order_data['order_date'], '2023-01-15')
#         self.assertEqual(order_data['currency'], 'EUR')
#         self.assertEqual(order_data['notes'], 'Basic test order for unit testing')
#         self.assertEqual(order_data['delivery_date'], '2023-01-30')
        
#         # Verify customer information
#         customer_info = order_data['customer_info']
#         self.assertEqual(customer_info['name'], 'Test Customer Ltd')
#         self.assertEqual(customer_info['vat'], 'BE0477472701')
#         self.assertEqual(customer_info['street'], '123 Test Street')
#         self.assertEqual(customer_info['city'], 'Brussels')
#         self.assertEqual(customer_info['zip'], '1000')
#         self.assertEqual(customer_info['country_code'], 'BE')
#         self.assertEqual(customer_info['email'], 'john.doe@testcustomer.com')
#         self.assertEqual(customer_info['phone'], '+32 2 123 4567')
        
#         # Verify order lines
#         order_lines = order_data['order_lines']
#         self.assertEqual(len(order_lines), 1)
        
#         line = order_lines[0]
#         self.assertEqual(line['product_code'], 'PROD-A-001')
#         self.assertEqual(line['product_name'], 'Test Product A')
#         self.assertEqual(line['description'], 'High quality test product for unit testing')
#         self.assertEqual(line['quantity'], 2.0)
#         self.assertEqual(line['unit_price'], 50.0)
#         self.assertEqual(line['line_extension_amount'], 100.0)

#     def test_parse_complex_order_xml(self):
#         """Test parsing of complex multi-line order XML document"""
#         xml_tree = self._load_xml_file('complex_order.xml')
        
#         order_data = self.proxy_user._parse_peppol_order_xml(xml_tree)
        
#         # Verify basic order information
#         self.assertEqual(order_data['order_number'], 'ORDER-COMPLEX-002')
#         self.assertEqual(order_data['currency'], 'USD')
        
#         # Verify customer information
#         customer_info = order_data['customer_info']
#         self.assertEqual(customer_info['name'], 'Global Enterprise Corp')
#         self.assertEqual(customer_info['vat'], 'US123456789')
#         self.assertEqual(customer_info['country_code'], 'US')
        
#         # Verify multiple order lines
#         order_lines = order_data['order_lines']
#         self.assertEqual(len(order_lines), 3)
        
#         # Check first line (product)
#         line1 = order_lines[0]
#         self.assertEqual(line1['product_code'], 'LAPTOP-PRO-X1')
#         self.assertEqual(line1['product_name'], 'Laptop Pro X1')
#         self.assertEqual(line1['quantity'], 5.0)
#         self.assertEqual(line1['unit_price'], 100.0)
        
#         # Check second line (product)
#         line2 = order_lines[1]
#         self.assertEqual(line2['product_code'], 'MOUSE-WIRELESS-PRO')
#         self.assertEqual(line2['product_name'], 'Wireless Mouse Pro')
#         self.assertEqual(line2['quantity'], 10.0)
#         self.assertEqual(line2['unit_price'], 30.0)
        
#         # Check third line (service)
#         line3 = order_lines[2]
#         self.assertEqual(line3['product_code'], 'SERVICE-IT-CONSULTING')
#         self.assertEqual(line3['product_name'], 'IT Consulting Service')
#         self.assertEqual(line3['quantity'], 20.0)
#         self.assertEqual(line3['unit_price'], 35.0)
#         self.assertEqual(line3['uom'], 'HUR')  # Hours

#     def test_parse_invalid_order_xml(self):
#         """Test parsing of invalid order XML document"""
#         xml_tree = self._load_xml_file('invalid_order.xml')
        
#         # Should not raise exception but handle missing fields gracefully
#         order_data = self.proxy_user._parse_peppol_order_xml(xml_tree)
        
#         # Order number should be None due to missing ID
#         self.assertIsNone(order_data['order_number'])
#         self.assertEqual(order_data['order_date'], '2023-02-01')
#         self.assertIsNone(order_data['currency'])  # Missing currency
        
#         # Customer info should be empty due to missing BuyerCustomerParty
#         customer_info = order_data['customer_info']
#         self.assertEqual(customer_info, {})
        
#         # Should have one order line but with missing fields
#         order_lines = order_data['order_lines']
#         self.assertEqual(len(order_lines), 1)
        
#         line = order_lines[0]
#         self.assertIsNone(line.get('product_code'))
#         self.assertIsNone(line.get('product_name'))
#         self.assertEqual(line['quantity'], 1.0)
#         self.assertEqual(line['unit_price'], 0.0)  # Missing price

#     def test_parse_malformed_xml(self):
#         """Test parsing of malformed XML document"""
#         # This should raise an exception due to malformed XML
#         with self.assertRaises(Exception):
#             self._load_xml_file('malformed_order.xml')

#     def test_extract_customer_info_complete(self):
#         """Test extraction of complete customer information"""
#         xml_tree = self._load_xml_file('basic_order.xml')
        
#         customer_info = self.proxy_user._extract_order_customer_info(xml_tree)
        
#         self.assertEqual(customer_info['name'], 'Test Customer Ltd')
#         self.assertEqual(customer_info['vat'], 'BE0477472701')
#         self.assertEqual(customer_info['street'], '123 Test Street')
#         self.assertEqual(customer_info['city'], 'Brussels')
#         self.assertEqual(customer_info['zip'], '1000')
#         self.assertEqual(customer_info['country_code'], 'BE')
#         self.assertEqual(customer_info['email'], 'john.doe@testcustomer.com')
#         self.assertEqual(customer_info['phone'], '+32 2 123 4567')

#     def test_extract_customer_info_missing(self):
#         """Test extraction when customer information is missing"""
#         xml_tree = self._load_xml_file('invalid_order.xml')
        
#         customer_info = self.proxy_user._extract_order_customer_info(xml_tree)
        
#         # Should return empty dict when BuyerCustomerParty is missing
#         self.assertEqual(customer_info, {})

#     def test_extract_order_lines_multiple(self):
#         """Test extraction of multiple order lines"""
#         xml_tree = self._load_xml_file('complex_order.xml')
        
#         order_lines = self.proxy_user._extract_order_lines(xml_tree)
        
#         self.assertEqual(len(order_lines), 3)
        
#         # Verify each line has required fields
#         for line in order_lines:
#             self.assertIn('quantity', line)
#             self.assertIn('unit_price', line)
#             self.assertGreater(line['quantity'], 0)

#     def test_extract_order_lines_empty(self):
#         """Test extraction when no order lines exist"""
#         # Create minimal XML without order lines
#         xml_content = '''<?xml version='1.0' encoding='UTF-8'?>
#         <Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2">
#             <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">TEST</cbc:ID>
#         </Order>'''
        
#         xml_tree = etree.fromstring(xml_content.encode())
        
#         order_lines = self.proxy_user._extract_order_lines(xml_tree)
        
#         self.assertEqual(order_lines, [])

#     def test_resolve_partner_existing_by_vat(self):
#         """Test resolving existing partner by VAT number"""
#         customer_info = {
#             'name': 'Test Customer Ltd',
#             'vat': 'BE0477472701',
#             'email': 'john.doe@testcustomer.com',
#         }
        
#         partner = self.proxy_user._resolve_peppol_order_partner(customer_info, self.env.company)
        
#         # Should find existing partner
#         self.assertEqual(partner, self.existing_partner)

#     def test_resolve_partner_existing_by_name_email(self):
#         """Test resolving existing partner by name and email when VAT doesn't match"""
#         customer_info = {
#             'name': 'Test Customer Ltd',
#             'vat': 'BE9999999999',  # Different VAT
#             'email': 'john.doe@testcustomer.com',
#         }
        
#         partner = self.proxy_user._resolve_peppol_order_partner(customer_info, self.env.company)
        
#         # Should find existing partner by name and email
#         self.assertEqual(partner, self.existing_partner)

#     def test_resolve_partner_create_new(self):
#         """Test creating new partner when none exists"""
#         customer_info = {
#             'name': 'Fresh Start Industries',
#             'vat': 'NL999888777B01',
#             'street': '999 Innovation Drive',
#             'city': 'Amsterdam',
#             'zip': '1012 AB',
#             'country_code': 'NL',
#             'email': 'e.vandenberg@freshstart.nl',
#             'phone': '+31 20 123 4567',
#         }
        
#         partner = self.proxy_user._resolve_peppol_order_partner(customer_info, self.env.company)
        
#         # Should create new partner
#         self.assertNotEqual(partner, self.existing_partner)
#         self.assertEqual(partner.name, 'Fresh Start Industries')
#         self.assertEqual(partner.vat, 'NL999888777B01')
#         self.assertEqual(partner.street, '999 Innovation Drive')
#         self.assertEqual(partner.city, 'Amsterdam')
#         self.assertEqual(partner.zip, '1012 AB')
#         self.assertEqual(partner.country_id.code, 'NL')
#         self.assertEqual(partner.email, 'e.vandenberg@freshstart.nl')
#         self.assertEqual(partner.phone, '+31 20 123 4567')
#         self.assertTrue(partner.is_company)
#         self.assertEqual(partner.customer_rank, 1)

#     def test_resolve_partner_missing_info(self):
#         """Test error when customer information is missing"""
#         with self.assertRaises(UserError) as cm:
#             self.proxy_user._resolve_peppol_order_partner({}, self.env.company)
        
#         self.assertIn('No customer information found', str(cm.exception))

#     def test_resolve_product_by_code(self):
#         """Test resolving product by seller item identification code"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         product, warning = sale_order._resolve_peppol_order_product(
#             'PROD-A-001', 'Test Product A', self.env.company
#         )
        
#         self.assertEqual(product, self.existing_product)
#         self.assertIsNone(warning)

#     def test_resolve_product_by_name(self):
#         """Test resolving product by name when code doesn't match"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         product, warning = sale_order._resolve_peppol_order_product(
#             'UNKNOWN-CODE', 'Laptop Pro X1', self.env.company
#         )
        
#         self.assertEqual(product, self.existing_product_by_name)
#         self.assertIsNone(warning)

#     def test_resolve_product_not_found(self):
#         """Test handling when product is not found"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         product, warning = sale_order._resolve_peppol_order_product(
#             'UNKNOWN-CODE', 'Unknown Product', self.env.company
#         )
        
#         self.assertIsNone(product)
#         self.assertIsNotNone(warning)
#         self.assertIn('Product not found', warning)
#         self.assertIn('UNKNOWN-CODE', warning)
#         self.assertIn('Unknown Product', warning)

#     def test_resolve_product_missing_info(self):
#         """Test handling when product information is missing"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         product, warning = sale_order._resolve_peppol_order_product(
#             None, None, self.env.company
#         )
        
#         self.assertIsNone(product)
#         self.assertIsNotNone(warning)
#         self.assertIn('Product information missing', warning)

#     def test_create_peppol_order_lines_with_existing_products(self):
#         """Test creating order lines with existing products"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         order_lines_data = [
#             {
#                 'product_code': 'PROD-A-001',
#                 'product_name': 'Test Product A',
#                 'description': 'Test description',
#                 'quantity': 2.0,
#                 'unit_price': 50.0,
#             }
#         ]
        
#         sale_order._create_peppol_order_lines(order_lines_data)
        
#         # Verify order line was created
#         self.assertEqual(len(sale_order.order_line), 1)
        
#         line = sale_order.order_line[0]
#         self.assertEqual(line.product_id, self.existing_product)
#         self.assertEqual(line.product_uom_qty, 2.0)
#         self.assertEqual(line.price_unit, 50.0)
#         self.assertEqual(line.name, 'Test description')

#     def test_create_peppol_order_lines_with_unmapped_products(self):
#         """Test creating order lines with unmapped products"""
#         sale_order = self.env['sale.order'].create({
#             'partner_id': self.existing_partner.id,
#         })
        
#         order_lines_data = [
#             {
#                 'product_code': 'UNKNOWN-PRODUCT',
#                 'product_name': 'Unknown Product',
#                 'description': 'Unknown product description',
#                 'quantity': 1.0,
#                 'unit_price': 100.0,
#             }
#         ]
        
#         sale_order._create_peppol_order_lines(order_lines_data)
        
#         # Verify order line was created with warning
#         self.assertEqual(len(sale_order.order_line), 1)
        
#         line = sale_order.order_line[0]
#         self.assertFalse(line.product_id)  # No product mapped
#         self.assertEqual(line.product_uom_qty, 1.0)
#         self.assertEqual(line.price_unit, 100.0)
#         self.assertIn('Unknown product description', line.name)
#         self.assertIn('Product not found', line.name)  # Warning added

#     def test_create_from_peppol_order(self):
#         """Test creating sale order from parsed Peppol order data"""
#         order_data = {
#             'order_number': 'ORDER-001',
#             'client_order_ref': 'PO-2023-001',
#             'notes': 'Test order notes',
#             'order_lines': [
#                 {
#                     'product_code': 'PROD-A-001',
#                     'product_name': 'Test Product A',
#                     'description': 'Test description',
#                     'quantity': 2.0,
#                     'unit_price': 50.0,
#                 }
#             ]
#         }
        
#         order = self.env['sale.order']._create_from_peppol_order(
#             order_data, self.existing_partner, self.env.company, 'received', 'test-uuid'
#         )
        
#         # Verify order was created correctly
#         self.assertEqual(order.partner_id, self.existing_partner)
#         self.assertEqual(order.company_id, self.env.company)
#         self.assertEqual(order.peppol_order_uuid, 'test-uuid')
#         self.assertEqual(order.peppol_order_state, 'received')
#         self.assertEqual(order.client_order_ref, 'PO-2023-001')
#         self.assertEqual(order.origin, 'Peppol Order ORDER-001')
#         self.assertEqual(order.note, 'Test order notes')
        
#         # Verify order line was created
#         self.assertEqual(len(order.order_line), 1)
#         line = order.order_line[0]
#         self.assertEqual(line.product_id, self.existing_product)
#         self.assertEqual(line.product_uom_qty, 2.0)
#         self.assertEqual(line.price_unit, 50.0)