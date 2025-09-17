# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_cii import TestAccountEdiUblCii
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestOrderEdiUbl(TestAccountEdiUblCii, SaleCommon):

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Need to enable pricelist and discount to compute discount price.
        cls._enable_pricelists()
        # `_enable_discount()` will not work because we need this group to enable on superuser
        cls.env['res.config.settings'].create({'group_discount_per_so_line': True}).execute()

        # Seller company: it should import PO and export SO
        supplier_company_data = cls.setup_other_company(name='Gestral Inc.', vat='US9357841')
        cls.supplier_company = supplier_company_data['company']
        cls.sale_tax = supplier_company_data['default_tax_sale']
        cls.test_supplier_partner = cls.env['res.partner'].create({
            'name': "Noco",
            'email': "noco@email.com",
            'parent_id': cls.supplier_company.partner_id.id
        })

        # Buyer company: it should import SO and export PO
        customer_company_data = cls.setup_other_company(name='Lumiere LLC', vat='US14001383')
        cls.customer_company = customer_company_data['company']
        cls.purchase_tax = customer_company_data['default_tax_purchase']
        cls.test_customer_partner = cls.env['res.partner'].create({
            'name': "Gustave",
            'email': "gustave@email.com",
            'parent_id': cls.customer_company.partner_id.id,
        })

        cls.displace_prdct.list_price = 100.0
        cls.place_prdct.list_price = 50.0

    def get_purchase_xml(self, po_line_vals, **po_vals):
        """ Helper function to generate the UBL xml of a purchase order from the customer company. """
        po = self.env['purchase.order'].with_company(self.customer_company).create({
            'name': 'New PO',
            'partner_id': self.supplier_company.partner_id.id,
            'order_line': [Command.create(vals) for vals in po_line_vals],
            **po_vals,
        })

        return self.env['ir.attachment'].create({
            'raw': self.env['purchase.edi.xml.ubl_bis3']._export_order(po),
            'name': 'test_purchase_order.xml',
        })

    def get_sale_xml(self, so_line_vals, **so_vals):
        """ Helper function to generate the UBL xml of a sale order from the supplier company. """
        so = self.env['sale.order'].with_company(self.supplier_company).create({
            'name': 'New SO',
            'partner_id': self.customer_company.partner_id.id,
            'order_line': [Command.create(vals) for vals in so_line_vals],
            **so_vals,
        })

        return self.env['ir.attachment'].create({
            'raw': self.env['sale.edi.xml.ubl_bis3']._export_order(so),
            'name': 'test_sale_order.xml',
        })

    def test_so_fallback_partner(self):
        """ Test partner assignation on a sale order when importing a PO xml. """

        # same name and VAT -> same partner
        self.env.user.company_id = self.supplier_company
        xml_attachment = self.get_purchase_xml([])
        so = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        self.assertEqual(so.partner_id, self.customer_company.partner_id)
        self.assertEqual(len(so.activity_ids), 0)

        # wrong name but same VAT -> same partner
        self.customer_company.name = "Paris Corp"
        so2 = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        self.assertEqual(so2.partner_id, self.customer_company.partner_id)
        self.assertEqual(len(so2.activity_ids), 0)

        # wrong name and wrong VAT -> new partner with the new name & new VAT, activity that a new partner was created
        self.customer_company.vat = "FR123456798"
        so3 = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        new_partner = self.env['res.partner'].search([], order='id DESC', limit=1)
        self.assertEqual(so3.partner_id, new_partner)
        self.assertEqual(len(so3.activity_ids), 1)
        self.assertEqual(so3.activity_ids.user_id, self.env.user)

        # wrong name and no VAT -> current user's partner_id with an activity in chatter
        self.customer_company.name = "Esquie's Nest"
        self.customer_company.vat = ""  # we need to remove the VAT before generating a new xml
        xml_attachment_4 = self.get_purchase_xml([])
        self.customer_company.name = "Lumiere LLC"
        self.customer_company.vat = "US14001383"
        so4 = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment_4)
        self.assertEqual(so4.partner_id, self.env.user.partner_id)
        self.assertEqual(len(so4.activity_ids), 1)
        self.assertEqual(so4.activity_ids.user_id, self.env.user)

    def test_po_fallback_partner(self):
        """ Test partner assignation on a sale order when importing a PO xml. """

        # same name and VAT -> same partner
        self.env.user.company_id = self.customer_company
        xml_attachment = self.get_sale_xml([])
        po = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        self.assertEqual(po.partner_id, self.supplier_company.partner_id)
        self.assertEqual(len(po.activity_ids), 0)

        # wrong name but same VAT -> same partner
        self.supplier_company.name = "Paris Corp"
        po2 = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        self.assertEqual(po2.partner_id, self.supplier_company.partner_id)
        self.assertEqual(len(po2.activity_ids), 0)

        # wrong name and wrong VAT -> new partner with the new name & new VAT, activity that a new partner was created
        self.supplier_company.vat = "FR123456798"
        po3 = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        new_partner = self.env['res.partner'].search([], order='id DESC', limit=1)
        self.assertEqual(po3.partner_id, new_partner)
        self.assertEqual(len(po3.activity_ids), 1)
        self.assertEqual(po3.activity_ids.user_id, self.env.user)

        # wrong name and no VAT -> current user's partner_id with an activity in chatter
        self.supplier_company.name = "Esquie's Nest"
        self.supplier_company.vat = ""  # we need to remove the VAT before generating a new xml
        xml_attachment_4 = self.get_sale_xml([])
        self.supplier_company.name = "Gestral Inc."
        self.supplier_company.vat = "US9357841"
        po4 = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment_4)
        self.assertEqual(po4.partner_id, self.env.user.partner_id)
        self.assertEqual(len(po4.activity_ids), 1)
        self.assertEqual(po4.activity_ids.user_id, self.env.user)

    def test_so_import_product_from_po(self):
        po_line_vals = [
            {
                'product_id': self.place_prdct.id,
                'price_unit': 30.0,
                'product_uom_id': self.uom_units.id,
                'product_qty': 10.0,
                'tax_ids': self.purchase_tax.ids,
                'discount': 10.0,
            }, {
                'product_id': self.displace_prdct.id,
                'price_unit': 30.0,
                'product_uom_id': self.uom_units.id,
                'product_qty': 50.0,
                'tax_ids': self.purchase_tax.ids,
                'discount': 0.0,
            },
        ]
        xml_attachment = self.get_purchase_xml(po_line_vals)
        so = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Should be able to confirm order
        so.action_confirm()
        self.assertEqual(so.partner_id, self.customer_company.partner_id)

        # Find first sale tax related to purchase tax
        related_sale_tax = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(so.company_id),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', self.purchase_tax.amount),
        ], limit=1)
        # Update lines vals depending on sale order field names
        for line in po_line_vals:
            line_product = self.env['product.product'].browse(line['product_id'])
            line['product_uom_qty'] = line.pop('product_qty')
            line['discount'] = 0.0
            # Set sales tax related to purchase tax
            line['tax_ids'] = related_sale_tax.ids
            line['price_unit'] = line_product.list_price

        self.assertRecordValues(so.order_line, po_line_vals)

    def test_po_import_product_from_so(self):
        so_line_vals = [
            {
                'product_id': self.place_prdct.id,
                'product_uom_id': self.uom_units.id,
                'product_uom_qty': 10.0,
                'tax_ids': self.sale_tax.ids,
                'discount': 10.0,
            }, {
                'product_id': self.displace_prdct.id,
                'product_uom_id': self.uom_units.id,
                'product_uom_qty': 50.0,
                'tax_ids': self.sale_tax.ids,
                'discount': 0.0,
            },
        ]
        xml_attachment = self.get_sale_xml(so_line_vals)
        po = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Should be able to confirm order
        po.button_confirm()
        self.assertEqual(po.partner_id, self.supplier_company.partner_id)

        # Find first purchase tax related to sale tax
        related_purchase_tax = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(po.company_id),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', self.sale_tax.amount),
        ], limit=1)
        # Update lines vals depending on purchase order field names
        for line in so_line_vals:
            line_product = self.env['product.product'].browse(line['product_id'])
            line['product_qty'] = line.pop('product_uom_qty')
            # Set purchase tax related to sale tax
            line['tax_ids'] = related_purchase_tax.ids
            line['price_unit'] = line_product.list_price

        self.assertRecordValues(po.order_line, so_line_vals)

    def test_so_product_unit_price_with_different_uom(self):
        po_line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 1100.0,
            'product_uom_id': self.uom_dozens.id,
            'product_qty': 5.0,
        }]
        xml_attachment = self.get_purchase_xml(po_line_vals)
        so = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Update lines vals depending on sale order field names
        for line in po_line_vals:
            line_product = self.env['product.product'].browse(line['product_id'])
            product_uom = self.env['uom.uom'].browse(line['product_uom_id'])
            line['product_uom_qty'] = line['product_qty']
            line['price_unit'] = line_product.uom_id._compute_price(line_product.list_price, product_uom)
            del line['product_qty']

        self.assertRecordValues(so.order_line, po_line_vals)

    def test_po_product_unit_price_with_different_uom(self):
        so_line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 1100.0,
            'product_uom_id': self.uom_dozens.id,
            'product_uom_qty': 5.0,
        }]
        xml_attachment = self.get_sale_xml(so_line_vals)
        po = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Update lines vals depending on purchase order field names
        for line in so_line_vals:
            line['product_qty'] = line.pop('product_uom_qty')

        self.assertRecordValues(po.order_line, so_line_vals)

    def test_so_no_matching_product_found(self):
        line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 80.0,
            'product_uom_id': self.uom_dozens.id,
        }]
        xml_attachment = self.get_purchase_xml(line_vals)
        self.displace_prdct.active = False
        so = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        with self.assertRaises(UserError):
            # Raise user error if line does not have product set
            so.action_confirm()
        line_vals[0]['product_id'] = False
        # Should set other values properly
        self.assertRecordValues(so.order_line, line_vals)
        # Should create an activity if product is not found
        self.assertEqual(len(so.activity_ids), 1)

    def test_po_no_matching_product_found(self):
        line_vals = [{
            'product_id': self.displace_prdct.id,
            'price_unit': 80.0,
            'product_uom_id': self.uom_dozens.id,
        }]
        xml_attachment = self.get_sale_xml(line_vals)
        self.displace_prdct.active = False
        po = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        line_vals[0]['product_id'] = False
        # Should set other values properly
        self.assertRecordValues(po.order_line, line_vals)
        # Should create an activity if product is not found
        self.assertEqual(len(po.activity_ids), 1)

    def test_so_import_payment_terms(self):
        payment_term = self.env.ref('account.account_payment_term_30days')
        xml_attachment = self.get_purchase_xml([], payment_term_id=payment_term.id)
        so = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Should have same payment term as PO
        self.assertEqual(so.payment_term_id, payment_term)

    def test_po_import_payment_terms(self):
        payment_term = self.env.ref('account.account_payment_term_30days')
        xml_attachment = self.get_sale_xml([], payment_term_id=payment_term.id)
        po = self.env['purchase.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(xml_attachment)
        # Should have same payment term as PO
        self.assertEqual(po.payment_term_id, payment_term)
