# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from odoo import fields, Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestAccountMoveImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_open_wood = cls.env['res.partner'].create({
            'name': 'openWood',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0219325116',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 33.06,
        })
        cls.tax_21 = cls.percent_tax(cls, 21.0, type_tax_use='purchase')
        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_open_wood.id,
            'date_order': fields.Date.today(),
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'name': cls.product.name,
                'product_qty': 1.0,
                'taxes_id': [Command.link(cls.tax_21.id)],
            })],
        })
        cls.purchase_order.button_confirm()

    def _create_bill_from_xml(self, xml_file_path, modifying_xpath=None):
        file_path = f"{self.test_module}/tests/test_files/{xml_file_path}"
        with file_open(file_path, 'rb') as file:
            xml_content = file.read()

        if modifying_xpath:
            xml_tree = etree.fromstring(xml_content)
            xml_tree = self.with_applied_xpath(xml_tree, modifying_xpath)
            xml_content = etree.tostring(xml_tree)

        xml_attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': 'test_bill.xml',
            'raw': xml_content,
        })
        return self._import_attachment(xml_attachment)

    def _import_attachment(self, attachment, journal=None):
        journal = journal or self.company_data["default_journal_purchase"]
        return self.env['account.journal'] \
            .with_context(default_journal_id=journal.id) \
            ._create_document_from_attachment(attachment.id)

    def test_po_matching_no_partner_override(self):
        """
        When importing a bill, and it matches with a purchase order, the partner on
        the bill should be the same as the po partner
        """
        # First, should set the parent as no child exists
        bill = self._create_bill_from_xml('ubl_bis3_po_partner.xml')
        expected_parent = [{
            'invoice_origin': self.purchase_order.name,
            'partner_id': self.partner_open_wood.id,
        }]
        self.assertRecordValues(bill, expected_parent)
        bill.unlink()

        # Then, create a child of 'invoice' type -> still should set the parent
        child = self.env['res.partner'].create({
            'name': 'Test Child openwood',
            'type': 'invoice',
            'parent_id': self.partner_open_wood.id,
        })

        bill = self._create_bill_from_xml('ubl_bis3_po_partner.xml')
        self.assertRecordValues(bill, expected_parent)

        # Finally, create a PO with the child as partner -> should find the child
        po_child = self.env['purchase.order'].create({
            'partner_id': child.id,
            'date_order': fields.Date.today(),
            'order_line': [Command.create({
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 1.0,
                'taxes_id': [Command.link(self.tax_21.id)],
            })],
        })
        po_child.button_confirm()
        bill_child = self._create_bill_from_xml('ubl_bis3_po_partner.xml')
        self.assertRecordValues(bill_child, [{
            'invoice_origin': po_child.name,
            'partner_id': child.id,
        }])

    def test_po_matching_invoice_line_without_name(self):
        """Purchase order matching should handle invoice lines without a name."""
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_open_wood.id,
            'date_order': fields.Date.today(),
            'partner_ref': 'my_match_reference',
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'product_qty': 1.0,
                    'price_unit': 33.06,
                    'taxes_id': [Command.link(self.tax_21.id)],
                }),
                Command.create({
                    'name': 'Transfer',
                    'product_qty': 1.0,
                    'price_unit': 10.00,
                    'taxes_id': [Command.link(self.tax_21.id)],
                }),
            ],
        })
        purchase_order.button_confirm()

        modifying_xpath = """
            <xpath expr="/*[local-name()='Invoice']/*[local-name()='InvoiceLine'][1]"
                position="before">
                <cac:AllowanceCharge
                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                    <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
                    <cbc:AllowanceChargeReasonCode>FC</cbc:AllowanceChargeReasonCode>
                    <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
                    <cac:TaxCategory>
                        <cbc:ID>S</cbc:ID>
                        <cbc:Percent>21.00</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:TaxCategory>
                </cac:AllowanceCharge>
            </xpath>
        """
        bill = self._create_bill_from_xml('ubl_bis3_po_partner.xml', modifying_xpath)

        bill._find_and_set_purchase_orders(
            ['my_match_reference'], bill.partner_id.id, bill.amount_total)

        self.assertIn(bill, purchase_order.invoice_ids)
