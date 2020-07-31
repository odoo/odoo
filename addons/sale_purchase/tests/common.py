# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import TestSaleCommon


class TestCommonSalePurchaseNoChart(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_dozen = cls.env.ref('uom.product_uom_dozen')

        # Create category
        cls.product_category_purchase = cls.env['product.category'].create({
            'name': 'Product Category with Income account',
            'property_account_income_categ_id': cls.company_data['default_account_expense'].id
        })

        cls.partner_vendor_service = cls.env['res.partner'].create({
            'name': 'Super Service Supplier',
            'email': 'supplier.serv@supercompany.com',
        })

        cls.service_purchase_1 = cls.env['product.product'].create({
            'name': "Out-sourced Service 1",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'SERV_DEL',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category_purchase.id,
            'service_to_purchase': True,
        })
        cls.service_purchase_2 = cls.env['product.product'].create({
            'name': "Out-sourced Service 2",
            'standard_price': 20.0,
            'list_price': 15.0,
            'type': 'service',
            'uom_id': uom_dozen.id,  # different UoM
            'uom_po_id': uom_unit.id,
            'invoice_policy': 'order',
            'expense_policy': 'no',
            'default_code': 'SERV_ORD',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category_purchase.id,
            'service_to_purchase': True,
        })

        cls.supplierinfo1 = cls.env['product.supplierinfo'].create({
            'name': cls.partner_vendor_service.id,
            'price': 100,
            'product_tmpl_id': cls.service_purchase_1.product_tmpl_id.id,
            'delay': 1,
        })
        cls.supplierinfo2 = cls.env['product.supplierinfo'].create({
            'name': cls.partner_vendor_service.id,
            'price': 10,
            'product_tmpl_id': cls.service_purchase_2.product_tmpl_id.id,
            'delay': 5,
        })
