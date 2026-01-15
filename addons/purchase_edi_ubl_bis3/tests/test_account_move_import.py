# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 40.0,
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_open_wood.id,
            'date_order': fields.Date.today(),
            'name': 'test_purchase_order',
            'order_line': [Command.create({
                'product_id': cls.product.id,
                'name': cls.product.name,
                'product_qty': 1.0,
            })],
        })
        cls.purchase_order.button_confirm()

    def _create_bill_from_xml(self, xml_file_path):
        file_path = f"{self.test_module}/tests/test_files/{xml_file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_bill.xml',
                'raw': file.read(),
            })
        return self._import_attachment(xml_attachment)

    def _import_attachment(self, attachment, journal=None):
        journal = journal or self.company_data["default_journal_purchase"]
        return self.env['account.journal'] \
            .with_context(default_journal_id=journal.id) \
            ._create_document_from_attachment(attachment.id)

    def test_import_purchase_order_reference_from_provided_field(self):
        """
        This test will try to match a purchase order when the purchase reference is in the provided field
        """
        bill = self._create_bill_from_xml("ubl_bis3_PO.xml")
        self.assertEqual(bill.invoice_origin, self.purchase_order.name)
        # Checks if all lines referencing a PO reference the PO we created in setup.
        # The 'or [False]' makes sure that there's at least one line referencing a PO.
        self.assertTrue(all([line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id] or [False]))

    def test_import_purchase_order_reference_from_lines_description(self):
        """
        This test will try to match a purchase order when the purchase reference is not
        in the provided field but in the lines descriptions
        """
        bill = self._create_bill_from_xml("ubl_bis3_PO_description.xml")
        self.assertEqual(bill.invoice_origin, self.purchase_order.name)
        # Checks if all lines referencing a PO reference the PO we created in setup.
        # The 'or [False]' makes sure that there's at least one line referencing a PO.
        self.assertTrue(all([line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id] or [False]))

    def test_multiple_purchase_order_references(self):
        """
        This test checks that we find the purchase_order_id when giving multiple possible
        references in the 'invoice_origin' field
        """
        # Test with reference
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_origin': 'TEST multiple references test_purchase_order and other refs',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 40,
            })]
        })
        bill._link_bill_origin_to_purchase_orders()
        self.assertEqual(bill.invoice_origin, 'test_purchase_order')
        self.assertTrue(all(line.purchase_order_id == self.purchase_order for line in bill.line_ids if line.purchase_order_id))

        # Test without ref
        bill_2 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_origin': 'TEST multiple references and other refs',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 40,
            })]
        })
        bill_2._link_bill_origin_to_purchase_orders()
        self.assertFalse(bill_2.invoice_origin)
        self.assertTrue(all(not line.purchase_order_id for line in bill_2.line_ids))
