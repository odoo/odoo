# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import file_open, mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_my_edi.tests.test_file_generation import NS_MAP
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyInvoisPoS(TestPoSCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        # Second config
        cash_journal = cls.env['account.journal'].create({
            'name': 'Other Cash Journal',
            'code': 'OCJ',
            'type': 'cash',
        })
        cash_payment = cls.env['pos.payment.method'].create({
            'name': 'Cash Payment',
            'journal_id': cash_journal.id,
            'receivable_account_id': cls.pos_receivable_cash.id,
            'company_id': cls.env.company.id,
        })
        cls.other_config = cls.config.copy()
        cls.other_config.payment_method_ids |= cash_payment

        cls.product_one = cls.create_product("Product 1", cls.categ_basic, 100, tax_ids=cls.taxes['tax7'].ids)
        cls.product_two = cls.create_product("Product 2", cls.categ_basic, 500, tax_ids=cls.taxes['tax7'].ids)
        (cls.product_one | cls.product_two).l10n_my_edi_classification_code = "022"

        cls.env.company.write({
            'name': 'MY Test Company',
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_kul').id,
            'zip': '50300',
            'street': '1 Wisma Dato Dagang',
            'street2': 'Jln Raja Alang Kampung Bahru Mala',
            'city': 'Kuala Lumpur',
            'phone': '+60123456789',
            'email': 'info@company.myexample.com',
        })
        cls.env.company.partner_id.l10n_my_edi_industrial_classification = cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')])
        cls.invoicing_customer = cls.customer
        cls.invoicing_customer.write({
            'vat': 'C2584563201',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234568',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456786',
        })

        cls.proxy_user = cls.env['account_edi_proxy_client.user']._register_proxy_user(cls.env.company, 'l10n_my_edi', 'demo')
        cls.proxy_user.edi_mode = 'test'

        # Prepare a PoS config in USD
        cls.usd_config = cls.other_config.copy()

        cls.foreign_currency = cls.setup_other_currency('USD')
        usd_pricelist = cls.env['product.pricelist'].create({
            'name': 'USD Pricelist',
            'currency_id': cls.foreign_currency.id,
        })
        pos_journal = cls.env['account.journal'].create({
            "name": "Point of Sale",
            "code": "POSUSD",
            "type": "general",
            "company_id": cls.env.company.id,
            "currency_id": cls.foreign_currency.id,
        })
        cash_journal_usd = cls.env['account.journal'].create({
            'name': 'Other Cash Journal',
            'code': 'CJU',
            'type': 'cash',
        })
        cash_payment_usd = cls.env['pos.payment.method'].create({
            'name': 'Cash Payment',
            'journal_id': cash_journal_usd.id,
            'receivable_account_id': cls.pos_receivable_cash.id,
            'company_id': cls.env.company.id,
        })

        cls.usd_config.write({
            'name': 'USD PoS Shop Test',
            'journal_id': pos_journal.id,
            'available_pricelist_ids': usd_pricelist.ids,
            'pricelist_id': usd_pricelist.id,
        })
        cls.usd_config.payment_method_ids |= cash_payment_usd

    ##################################
    # Base tests: consolidated invoice
    ##################################

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices(self):
        """ Creates and consolidate a few pos Order, then generate the consolidated invoice xml file. """
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            # Assert the amount of consolidated invoices
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)  # One consolidated invoice holds up to 100 lines
            # Get the XML File, and assert the amount of lines
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)  # Both orders are continuous, so they are merged in a single line.
            # Finally, assert a few nodes to make sure the file make sense (line amount, customer tin (general one), ...
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '600.00')
            self._assert_node_values(xml_tree, "cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID", 'EI00000000010')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_with_split(self):
        """ Make sure that when orders are not continuous, we split them in multiple lines. """
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})
                third_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | third_order).consolidated_invoice_ids
            # Get the XML File, and assert the amount of lines
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            # There is an invoiced order between both consolidated orders, so there is two lines
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            # Finally, ensure that the line values are correct.
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '100.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '500.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_from_multiple_configs(self):
        """ When consolidating from multiple configs at once, we expect one Consolidated Invoice per config. """
        orders = self.env['pos.order']
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
            self.config = self.other_config  # Switch config
            with self.with_pos_session():
                orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})

        with freeze_time("2025-01-02"):
            with self.with_pos_session():
                orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            self.config = self.basic_config  # Switch config
            with self.with_pos_session():
                orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
        # Consolidate them
        wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'consolidation_type': 'pos',
        })
        wizard.button_consolidate()
        consolidated_invoice = orders.consolidated_invoice_ids
        self.assertEqual(len(consolidated_invoice), 2)  # One consolidated invoice holds up to 100 lines
        config1, config2 = consolidated_invoice
        self.assertEqual(config1.linked_order_count, 2)
        self.assertEqual(config2.linked_order_count, 3)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_limit(self):
        """ Consolidate multiple orders by lowering the allowed amount of lines """
        with freeze_time("2025-01-01"):
            # Create two orders split in the middle to create two lines.
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})
                third_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})

            with patch('odoo.addons.l10n_my_edi_pos.wizard.myinvois_consolidate_invoice_wizard.MAX_LINE_COUNT_PER_INVOICE', 1):
                # Consolidate them
                wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                    'date_from': '2025-01-01',
                    'date_to': '2025-01-31',
                    'consolidation_type': 'pos',
                })
                wizard.button_consolidate()
                consolidated_invoice = (first_order | third_order).consolidated_invoice_ids
                self.assertEqual(len(consolidated_invoice), 2)  # Two consolidated invoices of a single line due to the MAX_LINE_COUNT_PER_INVOICE

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_prepayment_unlink(self):
        """Ensure that consolidated invoices have a PaidAmount of 0.00 and the correct PayableAmount."""
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})

            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()

            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)

            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            tax_inclusive_node = xml_tree.xpath("cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount", namespaces=NS_MAP)
            self.assertTrue(tax_inclusive_node, "TaxInclusiveAmount node is missing from the XML.")
            expected_total = tax_inclusive_node[0].text

            self._assert_node_values(xml_tree, "cac:PrepaidPayment/cbc:PaidAmount", '0.00')
            self._assert_node_values(xml_tree, "cac:LegalMonetaryTotal/cbc:PayableAmount", expected_total)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_individual_invoice_prepayment_unlink(self):
        """Ensure that individual POS e-invoices have a PaidAmount of 0.00 and the correct PayableAmount."""
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})

            invoice = order.account_move
            xml_tree = etree.fromstring(invoice._get_active_myinvois_document().myinvois_file_id.raw)
            tax_inclusive_node = xml_tree.xpath("cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount", namespaces=NS_MAP)
            self.assertTrue(tax_inclusive_node, "TaxInclusiveAmount node is missing from the XML.")
            expected_total = tax_inclusive_node[0].text

            self._assert_node_values(xml_tree, "cac:PrepaidPayment/cbc:PaidAmount", '0.00')
            self._assert_node_values(xml_tree, "cac:LegalMonetaryTotal/cbc:PayableAmount", expected_total)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_send_consolidated_invoice(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()
                self.assertRecordValues(consolidated_invoice, [{
                    'myinvois_submission_uid': '123456789',
                    'myinvois_external_uuid': '123458974513518',
                    'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
                }])

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_send_multiple_consolidated_invoice(self):
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
            self.config = self.other_config  # Switch config
            with self.with_pos_session():
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()
                self.assertRecordValues(consolidated_invoice, [{
                    'myinvois_submission_uid': '123456789',
                    'myinvois_external_uuid': '123458974513518',
                    'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
                }, {
                    'myinvois_submission_uid': '123456789',
                    'myinvois_external_uuid': '123458974513519',
                    'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
                }])

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_invoice_from_pos(self):
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})
            self.assertRecordValues(order.account_move._get_active_myinvois_document(), [{
                'myinvois_submission_uid': '123456789',
                'myinvois_external_uuid': '123458974513518',
                'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
                'myinvois_document_long_id': '123-789-654',
            }])

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_delete_consolidated_invoice(self):
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            # We can delete consolidated orders that are in Draft (unsent)
            consolidated_invoice.unlink()
            self.assertFalse(consolidated_invoice.exists())
            # Redo another consolidated invoice, but send it.
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()
            # We cannot delete a sent invoice (validation in progress, or valid)
            with self.assertRaises(UserError):
                consolidated_invoice.unlink()
            # We cancel it
            cancellation_wizard = self.env['myinvois.document.status.update.wizard'].with_context(
                default_document_id=consolidated_invoice.id, default_new_status='cancelled',
            ).create({'reason': 'Test'})
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                cancellation_wizard.button_request_update()
            # We can unlink after cancellation
            consolidated_invoice.unlink()
            self.assertFalse(consolidated_invoice.exists())

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_nothing_to_consolidate(self):
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                    'date_from': '2025-01-01',
                    'date_to': '2025-01-31',
                    'consolidation_type': 'pos',
                })
                # As the session isn't closed yet, the order isn't available to consolidate so we raise an exception.
                with self.assertRaises(ValidationError):
                    wizard.button_consolidate()

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_in_foreign_currency(self):
        """
        Creates and consolidate a few pos Order, then generate the consolidated invoice xml file.
        This is done in a PoS config with a currency different than the company's currency.
        """

        self.config = self.usd_config
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            # Assert the amount of consolidated invoices
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)  # One consolidated invoice holds up to 100 lines
            # Get the XML File, and assert the amount of lines
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)  # Both orders are continuous, so they are merged in a single line.
            # Finally, assert a few nodes to make sure the file make sense (line amount, customer tin (general one), ...
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '1200.00')
            self._assert_node_values(xml_tree, "cac:TaxExchangeRate/cbc:CalculationRate", '0.5')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_with_different_discounts(self):
        """
        Creates and consolidate a few pos Order, then generate the consolidated invoice xml file.
        We add separate discounts to the orders and ensure that they are correctly reflected after merging the lines.
        """
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0, 25)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0, 15)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            # Assert the amount of consolidated invoices
            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)  # One consolidated invoice holds up to 100 lines
            # Get the XML File, and assert the amount of lines
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)
            # product 1 price is 100 and we applied a 25% discount => subtotal should be 75, 25 of discount
            # product 2 price is 500 and we applied a 15% discount => subtotal should be 425, 75 of discount

            # Unit price is the undiscounted total
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cac:Price/cbc:PriceAmount", '600.0')
            # Both 'extension' amounts are the subtotal after applying discounts
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '500.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cac:ItemPriceExtension/cbc:Amount", '500.00')
            # And the discount should be 100
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cac:AllowanceCharge/cbc:Amount", '100.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_with_tax_included_in_price(self):
        """ Test that price_include taxes don't incorrectly appear as discounts in XML. """
        tax_included = self.env['account.tax'].create({
            'name': "10% Included",
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'l10n_my_tax_type': '01',
        })
        product = self.create_product("Product", self.categ_basic, 110, tax_ids=tax_included.ids)

        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                order = self._create_order({'pos_order_lines_ui_args': [(product, 1.0)]})
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            order.consolidated_invoice_ids.action_generate_xml_file()
            root = etree.fromstring(order.consolidated_invoice_ids.myinvois_file_id.raw)
            with file_open('l10n_my_edi_pos/tests/expected_xmls/consolidated_invoice_tax_included.xml', 'rb') as f:
                expected_xml = etree.fromstring(f.read())
            self.assertXmlTreeEqual(root, expected_xml)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_with_tax_included_in_price_and_discount(self):
        """ Test that price_include taxes with actual discounts work correctly. """
        tax_included = self.env['account.tax'].create({
            'name': "10% Included",
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'l10n_my_tax_type': '01',
        })
        product = self.create_product("Product", self.categ_basic, 110, tax_ids=tax_included.ids)

        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                order = self._create_order({'pos_order_lines_ui_args': [(product, 1.0, 20)]})
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            order.consolidated_invoice_ids.action_generate_xml_file()
            root = etree.fromstring(order.consolidated_invoice_ids.myinvois_file_id.raw)
            with file_open('l10n_my_edi_pos/tests/expected_xmls/consolidated_invoice_tax_included_with_discount.xml', 'rb') as f:
                expected_xml = etree.fromstring(f.read())
            self.assertXmlTreeEqual(root, expected_xml)

    #########
    # Refunds
    #########

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_refund_order(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -1.0,  # Refund 1 unit of product_b
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ],
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = self.env['myinvois.document'].search([])
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)
            # The refunded order and its refund has been excluded from the line.
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '500.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cac:Price/cbc:PriceAmount", '500.0')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_refund_order_partially(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -1.0,  # Refund 1 unit of product_b
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ],
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = self.env['myinvois.document'].search([])
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)
            # The refunded amount is removed from the line
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '600.00')
            # The displayed reference range only covers the normal orders, the refund isn't part of it.
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cac:Item/cbc:Name", f'{first_order.name}-{second_order.name}')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_refund_order_multiple_partial_refunds_completing_it(self):
        """ Several partial refunds that cumulatively refund an order fully should behave like a single full refund. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {'product': self.product_one, 'quantity': -1.0, 'refunded_orderline_id': first_order.lines[0].id},
                    ],
                })
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {'product': self.product_one, 'quantity': -1.0, 'refunded_orderline_id': first_order.lines[0].id},
                    ],
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = second_order.consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)
            # The two refunds together fully refund first_order, so it and both refunds are excluded entirely.
            self._assert_node_values(xml_tree, "cac:InvoiceLine/cbc:LineExtensionAmount", '500.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_refund_order_splits_continuous_group(self):
        """ A fully refunded order in the middle of an otherwise continuous run must split it into two lines. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                order_1 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                order_2 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                order_3 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {'product': self.product_one, 'quantity': -1.0, 'refunded_orderline_id': order_2.lines[0].id},
                    ],
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (order_1 | order_3).consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            # order_2 (fully refunded) and its refund are excluded, splitting order_1 and order_3 into two lines.
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '100.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", order_1.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '100.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", order_3.name)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_out_of_order_confirmation(self):
        """ An order can be held in the PoS UI and confirmed after later ones: it then keeps its (lower) ticket
        number/reference but ends up with a higher `sequence_number` (assigned when it reaches the database) than
        orders confirmed before it. `sequence_number` continuity alone would then group it with orders it isn't
        visually consecutive with (e.g. it would land next to order_20's receipt number instead of order_16/order_18's).
        Requiring the receipt reference to also be consecutive prevents that: every order that isn't visually
        adjacent to its `sequence_number` neighbour gets its own line instead of being merged into a misleading
        or unreadable one. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                # Orders are confirmed in this order: 16, 18, 19, 20, then 17 (held back and confirmed last).
                # Each keeps the reference/name matching its ticket number, regardless of confirmation order.
                order_16 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '250-1-000016'}})
                order_18 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '250-1-000018'}})
                order_19 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '250-1-000019', 'state': 'draft'}})
                order_20 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '250-1-000020'}})
                order_17 = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '250-1-000017'}})
                order_19.action_pos_order_cancel()

            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (order_16 | order_17 | order_18 | order_20).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)

            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            # None of the sequence_number-adjacent pairs (16/18 and 20/17) are also reference-consecutive,
            # so every order ends up on its own line instead of a misleading/unreadable merged one.
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 4)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", order_16.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", order_18.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[3]/cac:Item/cbc:Name", order_20.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[4]/cac:Item/cbc:Name", order_17.name)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_different_devices_not_merged(self):
        """ The receipt number is a counter local to a single device: two orders rung up on different devices can
        carry numbers that look consecutive by coincidence without the receipts actually being adjacent. They must
        not be merged into a single line just because `sequence_number` happens to be continuous too. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                order_a = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '2501-5-000005'}})
                order_b = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)], 'pos_order_ui_args': {'pos_reference': '2502-5-000006'}})

            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (order_a | order_b).consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)

            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            # sequence_number is continuous (created back to back), and the receipt numbers look consecutive
            # (5 then 6), but they come from different devices: they must not be merged into one line.
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", order_a.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", order_b.name)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order', 'odoo.addons.point_of_sale.models.pos_session')
    def test_refund_constrains_consolidated_invoice(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)]})
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = self.env["myinvois.document"].search([])
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                # Fails, the order should be invoiced in such a case
                with self.assertRaises(UserError):
                    self._create_order({
                        'pos_order_ui_args': {
                            'is_refund': True,
                        },
                        'pos_order_lines_ui_args': [
                            {
                                'product': self.product_one,
                                'quantity': -1.0,  # Refund 1 unit of product_b
                                'refunded_orderline_id': first_order.lines[0].id,
                            },
                        ],
                    })
                # If it is, it will work
                self.invoicing_customer.write({'vat': 'EI00000000010', 'l10n_my_identification_number': 'NA'})
                self._create_order({
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -1.0,  # Refund 1 unit of product_b
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ], 'customer': self.invoicing_customer, 'is_invoiced': True,
                })

    @mute_logger('odoo.addons.point_of_sale.models.pos_order', 'odoo.addons.point_of_sale.models.pos_session')
    def test_refund_constrains_regular_invoice(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})

            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                # Fails, the order should be invoiced in such a case
                with self.assertRaises(UserError):
                    self._create_order({
                        'pos_order_ui_args': {
                            'is_refund': True,
                        },
                        'pos_order_lines_ui_args': [
                            {
                                'product': self.product_one,
                                'quantity': -1.0,  # Refund 1 unit of product_b
                                'refunded_orderline_id': first_order.lines[0].id,
                            },
                        ],
                    })
                # If invoicing is checked, it will work.
                self._create_order({
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -1.0,  # Refund 1 unit of product_b
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ], 'customer': self.invoicing_customer, 'is_invoiced': True,
                })

    @mute_logger('odoo.addons.point_of_sale.models.pos_order', 'odoo.addons.point_of_sale.models.pos_session')
    def test_refund_constrains_not_submitted(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)]})
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                # Fails, you shouldn't invoice an order that hasn't been sent to myinvois yet.
                with self.assertRaises(UserError):
                    self._create_order({
                        'pos_order_lines_ui_args': [
                            {
                                'product': self.product_one,
                                'quantity': -1.0,  # Refund 1 unit of product_b
                                'refunded_orderline_id': first_order.lines[0].id,
                            },
                        ], 'customer': self.invoicing_customer, 'is_invoiced': True,
                    })
                self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -1.0,  # Refund 1 unit of product_b
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ],
                })

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_refund_with_customer(self):
        """
        When an order has a customer set, Odoo enforces that the refund must use the same customer.
        In the case of consolidated invoices, this does not make sense. So while we let Odoo set the correct customer,
        we must ensure that in the XML we use the general public as customer.
        """
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)], 'customer': self.invoicing_customer})

            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order.consolidated_invoice_ids.action_submit_to_myinvois()

            # We then create the refund for the order
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                self._create_order({
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product_one,
                            'quantity': -2.0,
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ], 'customer': self.invoicing_customer, 'is_invoiced': True,
                })

            refund = self.env['account.move'].search([('move_type', '=', 'out_refund')], limit=1, order='id desc')
            self.assertEqual(refund.partner_id, self.invoicing_customer)  # We have the correct customer on the refund.
            xml_tree = etree.fromstring(refund._get_active_myinvois_document().myinvois_file_id.raw)
            # But in the xml, we have the general public.
            self._assert_node_values(xml_tree, "cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID", 'EI00000000010')

    ###########
    # Test XMLs
    ###########

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_export_xml(self):
        """ Generate a relatively complex use case, and compare it to an XML file in order to ensure correct generation of the file. """
        tax_5 = self.env['account.tax'].create({
            'name': "5%",
            'amount_type': 'percent',
            'amount': 5,
            'l10n_my_tax_type': '01',
        })
        tax_10 = self.env['account.tax'].create({
            'name': "10%",
            'amount_type': 'percent',
            'amount': 10,
            'l10n_my_tax_type': '01',
        })

        product_1 = self.create_product("Product 1", self.categ_basic, 100, tax_ids=tax_5.ids)
        product_2 = self.create_product("Product 1", self.categ_basic, 10, tax_ids=tax_10.ids)

        self.config = self.usd_config
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                first_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 2.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 1.0)]})
                # This one has a 25% discount
                third_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 4.0, 25)]})
                fourth_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 2.0)]})
                # This one is invoiced right away, so it will not be consolidated.
                self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})
                fifth_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 1.0)]})

            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order | third_order | fourth_order | fifth_order).consolidated_invoice_ids
            # We expect a single invoice
            self.assertEqual(len(consolidated_invoice), 1)
            # Add an export custom number; it doesn't make much sense in this flow but supporting it may be useful.
            consolidated_invoice.myinvois_custom_form_reference = '123456789'
            # Get the XML File, and assert the amount of lines
            consolidated_invoice.action_generate_xml_file()
            root = etree.fromstring(consolidated_invoice.myinvois_file_id.raw)
            with file_open('l10n_my_edi_pos/tests/expected_xmls/consolidated_invoice.xml', 'rb') as f:
                expected_xml = etree.fromstring(f.read())
            self.assertXmlTreeEqual(root, expected_xml)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_refund_export_xml(self):
        """ Generate a relatively complex use case, and compare it to an XML file in order to ensure correct generation of the file. """
        tax_5 = self.env['account.tax'].create({
            'name': "5%",
            'amount_type': 'percent',
            'amount': 5,
            'l10n_my_tax_type': '01',
        })
        tax_10 = self.env['account.tax'].create({
            'name': "10%",
            'amount_type': 'percent',
            'amount': 10,
            'l10n_my_tax_type': '01',
        })

        product_1 = self.create_product("Product 1", self.categ_basic, 100, tax_ids=tax_5.ids)
        product_2 = self.create_product("Product 1", self.categ_basic, 10, tax_ids=tax_10.ids)

        self.config = self.usd_config
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                # This one gets a customer, we will refund it later. It will cover refund + refund of consolidated order with customer
                first_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 2.0)], 'customer': self.invoicing_customer})
                second_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 1.0)]})
                # This one has a 25% discount
                third_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 4.0, 25)]})
                fourth_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 2.0)]})
                # This one is invoiced right away, so it will not be consolidated.
                self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})
                fifth_order = self._create_order({'pos_order_lines_ui_args': [(product_1, 1.0), (product_2, 1.0)]})

            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = (first_order | second_order | third_order | fourth_order | fifth_order).consolidated_invoice_ids
            # We expect a single invoice
            self.assertEqual(len(consolidated_invoice), 1)
            # Add an export custom number; it doesn't make much sense in this flow but supporting it may be useful.
            consolidated_invoice.myinvois_custom_form_reference = '123456789'
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()

            # We then create the refund for the first_order
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                self._create_order({
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                    'pos_order_lines_ui_args': [
                        {
                            'product': product_1,
                            'quantity': -2.0,
                            'refunded_orderline_id': first_order.lines[0].id,
                        },
                    ], 'customer': self.invoicing_customer, 'is_invoiced': True,
                })

            refund = self.env['account.move'].search([('move_type', '=', 'out_refund')], limit=1, order='id desc')
            root = etree.fromstring(refund._get_active_myinvois_document().myinvois_file_id.raw)
            with file_open('l10n_my_edi_pos/tests/expected_xmls/consolidated_invoice_refund.xml', 'rb') as f:
                expected_xml = etree.fromstring(f.read())
            self.assertXmlTreeEqual(root, expected_xml)

    def test_consolidate_invoices_with_year_range_sequence(self):
        with freeze_time("2026-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
            # Consolidate them
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2026-01-01',
                'date_to': '2026-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = first_order.consolidated_invoice_ids
            consolidated_invoice.name = "POS/2025-2026/000001"
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                consolidated_invoice.action_submit_to_myinvois()
            self.assertTrue(consolidated_invoice.myinvois_file_id)

    #################
    # Patched methods
    #################

    def _mock_successful_submission(self, endpoint, params):
        """ Mock a simple successful submission of N documents, matching the amount of documents in the params. """
        # Store the uuid/long_id in the params['documents'] so that we can more easily build the results.
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            for i, document in enumerate(params['documents']):
                document['uuid'] = f'12345897451351{8 + i}'
                document['long_id'] = f'123-789-65{4 + i}'

            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': document['move_id'],
                    'uuid': document['uuid'],
                    'success': True,
                } for document in params['documents']],
            }
        if endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    f'12345897451351{8 + i}': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': f'123-789-65{4 + i}',
                        'valid_datetime': '2025-01-01T01:00:00Z',
                    } for i in range(10)
                },
                'document_count': 10,
            }
        if endpoint == 'api/l10n_my_edi/1/update_status':
            return {
                'success': True,
            }
        raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    #########
    # Helpers
    #########

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, ui_data):
        return next(iter(self._create_orders([ui_data]).values()))

    def _assert_node_values(self, root, node_path, text, attributes=None):
        node = root.xpath(node_path, namespaces=NS_MAP)

        assert node, f'The requested node has not been found: {node_path}'

        self.assertEqual(
            node[0].text,
            text,
        )
        if attributes:
            for attribute, value in attributes.items():
                self.assertEqual(
                    node[0].attrib[attribute],
                    value,
                )
