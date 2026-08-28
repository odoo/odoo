# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree, html

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tools import file_open, mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_my_edi.tests.test_file_generation import NS_MAP
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyInvoisPoS(TestPoSCommon, HttpCase):

    _test_user_groups = None  # FIXME list needed groups

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
            'type': 'cash',
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
            "type": "sale",
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
            'type': 'cash',
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
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
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
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            # There is an invoiced order between both consolidated orders, so there is two lines
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            # Finally, ensure that the line values are correct.
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '100.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '500.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_split_on_different_devices(self):
        """ Two receipts taken on different devices are never reported on the same line, even when their order
        sequence numbers follow each other: each device numbers its own receipts. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
                first_order.pos_reference = f'251-{self.config.id}-000001'
                second_order.pos_reference = f'252-{self.config.id}-000002'

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '100.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '500.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_split_on_interleaved_devices(self):
        """ `sequence_number` counts for the whole config while each device numbers its own receipts, so a receipt
        taken on another device in between gaps the two receipts around it: they are reported on two lines although
        they do follow each other on their own device. We voluntarily accept these extra lines, `sequence_number`
        being the only one of the two counters the server assigns itself. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
                third_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                # Receipts 1 and 2 of device 1, with the first receipt of device 2 rung up in between: their
                # `sequence_number`, counted by the config, runs 1-2-3 over the three of them.
                first_order.pos_reference = f'251-{self.config.id}-000001'
                second_order.pos_reference = f'252-{self.config.id}-000001'
                third_order.pos_reference = f'251-{self.config.id}-000002'

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            consolidated_invoice = (first_order | second_order | third_order).consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 3)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", first_order.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", second_order.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[3]/cac:Item/cbc:Name", third_order.name)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_split_on_receipt_number_gap(self):
        """ An order can be recorded, and thus get its sequence number, later than its receipt was opened - it was
        held while later customers were served - so following sequence numbers alone don't make two receipts
        consecutive. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
                first_order.pos_reference = f'250-{self.config.id}-000001'
                second_order.pos_reference = f'250-{self.config.id}-000003'

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            consolidated_invoice = (first_order | second_order).consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", first_order.name)
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", second_order.name)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_keeps_continuous_orders_on_one_line(self):
        """ Receipts that follow each other on both counters are reported as a single "first-last" range. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                orders = self.env['pos.order']
                for _ in range(3):
                    orders |= self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            consolidated_invoice = orders.consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 1)
            self._assert_node_values(
                xml_tree,
                "cac:InvoiceLine[1]/cac:Item/cbc:Name",
                f'{orders[0].name}-{orders[-1].name}',
            )
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '300.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_linked_orders_are_listed_in_reporting_order(self):
        """ The linked orders are listed in the order in which they are reported on the consolidated invoice,
        instead of the reverse chronological order used by default for PoS orders. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            action = first_order.consolidated_invoice_ids.action_view_linked_orders()
            list_view = self.env.ref('l10n_my_edi_pos.view_pos_order_tree_consolidated')
            self.assertEqual(action['views'][0], (list_view.id, 'list'))
            self.assertIn(
                'default_order="sequence_number asc"',
                self.env['pos.order'].get_view(list_view.id, 'list')['arch'],
            )
            self.assertEqual(
                self.env['pos.order'].search(action['domain'], order='sequence_number asc').ids,
                (first_order | second_order).ids,
            )

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_consolidate_invoices_split_refunds_from_sales(self):
        """ Refund receipts are never merged into the line of the sales they follow, even when they are the very
        next receipts: the sales would otherwise be hidden inside a total that nets them out. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            with self.with_pos_session():
                self._create_order({'pos_order_lines_ui_args': [
                    {'product': self.product_one, 'quantity': -1.0, 'refunded_orderline_id': first_order.lines[0].id},
                ]})
                self._create_order({'pos_order_lines_ui_args': [
                    {'product': self.product_two, 'quantity': -1.0, 'refunded_orderline_id': second_order.lines[0].id},
                ]})
            first_refund = first_order.lines.refund_orderline_ids.order_id
            second_refund = second_order.lines.refund_orderline_ids.order_id

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            consolidated_invoice = first_order.consolidated_invoice_ids
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            # All four receipts follow each other, but the sales and the refunds are reported apart.
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            self._assert_node_values(
                xml_tree, "cac:InvoiceLine[1]/cac:Item/cbc:Name", f'{first_order.name}-{second_order.name}',
            )
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '600.00')
            self._assert_node_values(
                xml_tree, "cac:InvoiceLine[2]/cac:Item/cbc:Name", f'{first_refund.name}-{second_refund.name}',
            )
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '-600.00')

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
        """Ensure that consolidated invoices omit the PrepaidPayment node entirely and report the correct
        PayableAmount."""
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
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            tax_inclusive_node = xml_tree.xpath("cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount", namespaces=NS_MAP)
            self.assertTrue(tax_inclusive_node, "TaxInclusiveAmount node is missing from the XML.")
            expected_total = tax_inclusive_node[0].text

            self.assertFalse(xml_tree.xpath("cac:PrepaidPayment", namespaces=NS_MAP), "PrepaidPayment node should be omitted when there is no genuine prepayment.")
            self._assert_node_values(xml_tree, "cac:LegalMonetaryTotal/cbc:PayableAmount", expected_total)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_individual_invoice_prepayment_unlink(self):
        """Ensure that individual POS e-invoices with no genuine prepayment omit the PrepaidPayment node
        entirely and report the correct PayableAmount."""
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)], 'customer': self.invoicing_customer, 'is_invoiced': True})

            invoice = order.account_move
            xml_tree = etree.fromstring(invoice._get_active_myinvois_document().myinvois_file_id.raw.content)
            tax_inclusive_node = xml_tree.xpath("cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount", namespaces=NS_MAP)
            self.assertTrue(tax_inclusive_node, "TaxInclusiveAmount node is missing from the XML.")
            expected_total = tax_inclusive_node[0].text

            self.assertFalse(xml_tree.xpath("cac:PrepaidPayment", namespaces=NS_MAP), "PrepaidPayment node should be omitted when there is no genuine prepayment.")
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
                    'name': 'CINV/2025/00002',
                    'myinvois_submission_uid': '123456789',
                    'myinvois_external_uuid': '123458974513518',
                    'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
                }, {
                    'name': 'CINV/2025/00001',
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
    def test_myinvois_state_on_consolidated_order(self):
        """ The state of the active consolidated invoice is mirrored on its PoS orders. """
        with freeze_time("2025-01-01"):
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                second_order = self._create_order({'pos_order_lines_ui_args': [(self.product_two, 1.0)]})
            orders = first_order | second_order

            # Not consolidated yet.
            self.assertEqual(orders.mapped('l10n_my_edi_state'), [False, False])

            self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()

            # The consolidated invoice exists but has not been sent yet: still no state.
            consolidated_invoice = orders.consolidated_invoice_ids
            self.assertEqual(len(consolidated_invoice), 1)
            self.assertFalse(consolidated_invoice.myinvois_state)
            self.assertEqual(orders.mapped('l10n_my_edi_state'), [False, False])

            with patch(CONTACT_PROXY_METHOD, new=self._mock_pending_submission):
                # Sent, but MyInvois has not validated it yet.
                consolidated_invoice.action_submit_to_myinvois()
                self.assertEqual(consolidated_invoice.myinvois_state, 'in_progress')
                self.assertEqual(orders.mapped('l10n_my_edi_state'), ['in_progress', 'in_progress'])

                # The status is fetched again later on, and is now final.
                consolidated_invoice.action_update_submission_status()
                self.assertEqual(consolidated_invoice.myinvois_state, 'valid')
                self.assertEqual(orders.mapped('l10n_my_edi_state'), ['valid', 'valid'])

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_myinvois_state_on_singly_invoiced_order(self):
        """ Test that an order invoiced on its own takes the state of its invoice """
        with freeze_time("2025-01-01"):
            with self.with_pos_session(), patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                uninvoiced_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
                invoiced_order = self._create_order({
                    'pos_order_lines_ui_args': [(self.product_two, 1.0)],
                    'customer': self.invoicing_customer,
                    'is_invoiced': True,
                })

            self.assertEqual(invoiced_order.account_move.l10n_my_edi_state, 'valid')
            self.assertEqual(invoiced_order.l10n_my_edi_state, 'valid')
            self.assertFalse(invoiced_order.consolidated_invoice_ids)

            # A non invoiced order still has an invoice from the session's closing entry but no state.
            self.assertTrue(uninvoiced_order.account_move)
            self.assertFalse(uninvoiced_order.account_move.l10n_my_edi_state)
            self.assertFalse(uninvoiced_order.l10n_my_edi_state)

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
            self.config.journal_id.currency_id = self.env.ref('base.USD')
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
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
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
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
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
    def test_consolidate_invoices_pos_sequence_mix(self):
        """
        Post and submit mixes of regular and PoS consolidated invoices, to ensure that the sequence calculation follows as expected.
        PoS consolidated invoices are expected to follow the in_invoice sequence of the invoice journal selected in the pos config.

        We will:
            - Create and submit one regular consolidated invoice
            - Create and submit one PoS consolidated invoice
            - Create and submit another regular consolidated invoice
            - Create and submit another PoS consolidated invoice

        We expect the sequences to correctly go from CINV/xxx/00001 to CINV/xxx/00004
        """
        def _make_accounting_conso_invoice():
            self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
            myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'invoice',
            }).button_consolidate()
            myinvois_document_id = myinvois_document_action['res_id']
            myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                myinvois_document.action_submit_to_myinvois()
            return myinvois_document

        def _make_pos_conso_invoice():
            with self.with_pos_session():
                self._create_order({'pos_order_lines_ui_args': [(self.product_one, 1.0)]})
            # Consolidate them
            myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            }).button_consolidate()
            myinvois_document_id = myinvois_document_action['res_id']
            myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
            with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
                myinvois_document.action_submit_to_myinvois()
            return myinvois_document

        with freeze_time("2025-01-01"):
            consolidated_invoices = _make_accounting_conso_invoice()
            consolidated_invoices |= _make_pos_conso_invoice()
            consolidated_invoices |= _make_accounting_conso_invoice()
            consolidated_invoices |= _make_pos_conso_invoice()

            self.assertRecordValues(consolidated_invoices, [{
                'name': 'CINV/2025/00001',
                'myinvois_submission_uid': '123456789',
                'myinvois_external_uuid': '123458974513518',
                'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
            }, {
                'name': 'CINV/2025/00002',
                'myinvois_submission_uid': '123456789',
                'myinvois_external_uuid': '123458974513518',
                'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
            }, {
                'name': 'CINV/2025/00003',
                'myinvois_submission_uid': '123456789',
                'myinvois_external_uuid': '123458974513518',
                'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
            }, {
                'name': 'CINV/2025/00004',
                'myinvois_submission_uid': '123456789',
                'myinvois_external_uuid': '123458974513518',
                'myinvois_validation_time': fields.Datetime.from_string('2025-01-01 01:00:00'),
            }])

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
            root = etree.fromstring(order.consolidated_invoice_ids.myinvois_file_id.raw.content)
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
            root = etree.fromstring(order.consolidated_invoice_ids.myinvois_file_id.raw.content)
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
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = self.env['myinvois.document'].search([])
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            # Both sales are reported together, and the refund on a line of its own.
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '600.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cac:Price/cbc:PriceAmount", '600.0')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '-100.00')

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_refund_order_partially(self):
        with freeze_time("2025-01-01"):
            # Create the orders
            with self.with_pos_session():
                first_order = self._create_order({'pos_order_lines_ui_args': [(self.product_one, 2.0)]})
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
                    'pos_order_ui_args': {
                        'is_refund': True,
                    },
                })
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            consolidated_invoice = self.env['myinvois.document'].search([])
            consolidated_invoice.action_generate_xml_file()
            xml_tree = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
            self.assertEqual(len(xml_tree.xpath("cac:InvoiceLine", namespaces=NS_MAP)), 2)
            # The refunded amount is reported on its own line instead of being deducted from the sales.
            self._assert_node_values(xml_tree, "cac:InvoiceLine[1]/cbc:LineExtensionAmount", '700.00')
            self._assert_node_values(xml_tree, "cac:InvoiceLine[2]/cbc:LineExtensionAmount", '-100.00')

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
            xml_tree = etree.fromstring(refund._get_active_myinvois_document().myinvois_file_id.raw.content)
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
            self.config.journal_id.currency_id = self.env.ref('base.USD')
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
            root = etree.fromstring(consolidated_invoice.myinvois_file_id.raw.content)
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
            self.config.journal_id.currency_id = self.env.ref('base.USD')  # Crappy patch
            wizard = self.env['myinvois.consolidate.invoice.wizard'].create({
                'date_from': '2025-01-01',
                'date_to': '2025-01-31',
                'consolidation_type': 'pos',
            })
            wizard.button_consolidate()
            orders = (first_order | second_order | third_order | fourth_order | fifth_order)
            self.assertEqual(orders.currency_id.name, 'USD')
            consolidated_invoice = orders.consolidated_invoice_ids
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
            root = etree.fromstring(refund._get_active_myinvois_document().myinvois_file_id.raw.content)
            with file_open('l10n_my_edi_pos/tests/expected_xmls/consolidated_invoice_refund.xml', 'rb') as f:
                expected_xml = etree.fromstring(f.read())
            self.assertXmlTreeEqual(root, expected_xml)

    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_portal_invoice_request_flow(self):
        """ Test the flow from the portal ticket validation to EDI submission. """
        with self.with_pos_session():
            order = self._create_order({
                "pos_order_lines_ui_args": [(self.product_one, 1.0)],
            })

        self.assertFalse(order.is_singly_invoiced)

        url = f"/pos/ticket/validate?access_token={order.access_token}"
        response = self.url_open(url)  # GET request to get csrf token
        self.assertEqual(response.status_code, 200)

        token_elements = html.fromstring(response.content).xpath(
            '//input[@name="csrf_token"]/@value',
        )
        self.assertTrue(token_elements, "CSRF token not found in the HTML tree")
        csrf_token = token_elements[0]

        requested_invoice_data = {
            'access_token': order.access_token,
            'name': 'Test Name',
            'vat': 'C2584563200',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'country_id': self.env.ref('base.my').id,
            'state_id': self.env.ref('base.state_my_kul').id,
            'zip': '50300',
            'street': '1 Wisma Dato Dagang',
            'city': 'Kuala Lumpur',
            'phone': '+60123456789',
            'email': 'test@example.com',
            'csrf_token': csrf_token,
        }

        with patch(CONTACT_PROXY_METHOD, new=self._mock_successful_submission):
            self.url_open(url=url, data=requested_invoice_data)

        self.assertTrue(order.account_move, "Invoice is not created")

        myinvois_document = order.account_move._get_active_myinvois_document()
        self.assertTrue(
            myinvois_document,
            "MyInvois document was not created",
        )
        self.assertIn(
            myinvois_document.myinvois_state,
            ("in_progress", "submitted", "valid"),
            f"Unexpected MyInvois state: {myinvois_document.myinvois_state}",
        )

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

    def _mock_pending_submission(self, endpoint, params):
        """ Mock a successful submission for which MyInvois did not return a final status yet.
        A later single document status fetch returns 'valid'. """
        if endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    f'12345897451351{8 + i}': {
                        'status': 'in_progress',
                        'reason': '',
                    } for i in range(10)
                },
                'document_count': 10,
            }
        if endpoint == 'api/l10n_my_edi/1/get_status':
            return {
                'status': 'valid',
                'long_id': '123-789-654',
                'valid_datetime': '2025-01-01T01:00:00Z',
            }
        return self._mock_successful_submission(endpoint, params)

    #########
    # Helpers
    #########

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        cash_pm = self.config._get_cash_payment_method()
        session.close_session_from_ui({
            cash_pm.id: 0,
        })

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
