# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_cii import TestAccountEdiUblCii


@tagged('post_install', '-at_install')
class TestOrderEdiUbl(TestAccountEdiUblCii):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_company = cls.company_data_2['company']

        cls.purchase_tax = cls.company_data_2['default_tax_purchase']
        cls.test_partner = cls.env['res.partner'].create({
            'name': "Test partner",
            'email': "abc@email.com",
            'company_id': cls.purchase_company.id,
        })
        cls.displace_prdct.list_price = 100.0
        cls.place_prdct.list_price = 50.0

    def get_xml_attachment_of_po(self, po_line_vals, **po_vals):
        po = self.env['purchase.order'].with_company(self.purchase_company).create({
            'name': 'New PO',
            'partner_id': self.test_partner.id,
            'order_line': [Command.create(vals) for vals in po_line_vals],
            **po_vals,
        })

        return self.env['ir.attachment'].create({
            'raw': self.env['purchase.edi.xml.ubl_bis3'].with_context(
                    allow_company_ids=[self.purchase_company.id],
                )._export_order(po),
            'name': 'test_order.xml',
        })

    def test_so_fallback_partner(self):
        """ Test default current partner set on product if no matching partner found. """
        xml_attachment = self.get_xml_attachment_of_po([])
        self.purchase_company.sudo().name = "New company"
        so = self.env['sale.order']._create_order_from_attachment(xml_attachment.ids)
        # Should set current user partner if no matching company found
        self.assertEqual(so.partner_id, self.env.user.partner_id)
        # Should create an activity if some details are missing on SO
        self.assertEqual(len(so.activity_ids), 1)
        self.assertEqual(so.activity_ids.user_id, self.env.user)

    def test_import_product_from_po(self):
        line_vals = [
            {
                'product_id': self.place_prdct.id,
                'price_unit': 30.0,
                'product_uom_id': self.uom_units.id,
                'product_qty': 10.0,
                'taxes_id': self.purchase_tax.ids,
            }, {
                'product_id': self.displace_prdct.id,
                'price_unit': 30.0,
                'product_uom_id': self.uom_units.id,
                'product_qty': 50.0,
                'taxes_id': self.purchase_tax.ids,
            },
        ]
        xml_attachment = self.get_xml_attachment_of_po(line_vals)
        so = self.env['sale.order']._create_order_from_attachment(xml_attachment.ids)
        # Should able to confirm order
        so.action_confirm()
        self.assertEqual(so.partner_id, self.purchase_company.partner_id)

        # Find first sale tax related to purchase tax
        related_sales_tax = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(so.company_id),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', self.purchase_tax.amount),
        ], limit=1)
        # Update lines vals depending on sale order field names
        for line in line_vals:
            line_product = self.env['product.product'].browse(line['product_id'])
            line['product_uom_qty'] = line['product_qty']
            # Set sales tax related to similer to purchase tax
            line['tax_ids'] = related_sales_tax.ids
            line['price_unit'] = line_product.list_price
            del line['product_qty']
            del line['taxes_id']

        self.assertRecordValues(so.order_line, line_vals)

    def test_product_unit_price_with_different_uom(self):
        line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 1100.0,
            'product_uom_id': self.uom_dozens.id,
            'product_qty': 5.0,
        }]
        xml_attachment = self.get_xml_attachment_of_po(line_vals)
        so = self.env['sale.order']._create_order_from_attachment(xml_attachment.ids)
        # Update lines vals depending on sale order field names
        for line in line_vals:
            line_product = self.env['product.product'].browse(line['product_id'])
            product_uom = self.env['uom.uom'].browse(line['product_uom_id'])
            line['product_uom_qty'] = line['product_qty']
            line['price_unit'] = line_product.uom_id._compute_price(line_product.list_price, product_uom)
            del line['product_qty']

        self.assertRecordValues(so.order_line, line_vals)

    def test_no_matching_product_found(self):
        line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 80.0,
            'product_uom_id': self.uom_dozens.id,
        }]
        xml_attachment = self.get_xml_attachment_of_po(line_vals)
        self.displace_prdct.active = False
        so = self.env['sale.order']._create_order_from_attachment(xml_attachment.ids)
        with self.assertRaises(UserError):
            # Raise user error if line does not have product set
            so.action_confirm()
        line_vals[0]['product_id'] = False
        # Should set other values properly
        self.assertRecordValues(so.order_line, line_vals)
        # Should create an activity if product is not found
        self.assertEqual(len(so.activity_ids), 1)

    def test_import_payment_terms(self):
        payment_term = self.env.ref('account.account_payment_term_30days')
        xml_attachment = self.get_xml_attachment_of_po([], payment_term_id=payment_term.id)
        so = self.env['sale.order']._create_order_from_attachment(xml_attachment.ids)
        # Should have same payment term as PO
        self.assertEqual(so.payment_term_id, payment_term)
