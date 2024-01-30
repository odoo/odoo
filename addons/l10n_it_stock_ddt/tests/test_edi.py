# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from freezegun import freeze_time
from odoo import tools
from odoo.tests import tagged, Form
from odoo.addons.l10n_it_edi.tests.common import TestItEdi

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiDDT(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # UoM
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')

        # Tax
        cls.tax_22 = cls.env['account.tax'].with_company(cls.company).create({
            'name': '22% test tax',
            'amount': 22.0,
            'amount_type': 'percent'
        })

        # Products and pricelist
        cls.default_pricelist = cls.env['product.pricelist'].with_company(cls.company).create({
            'name': 'default_pricelist',
            'currency_id': cls.company.currency_id.id,
        })
        product_category = cls.env['product.category'].with_company(cls.company).create({'name': 'Test category'})
        cls.products = cls.env['product.product'].with_company(cls.company).create([
            {
                'name': 'product_service_delivery',
                'categ_id': product_category.id,
                'standard_price': 200.0,
                'list_price': 180.0,
                'type': 'service',
                'uom_id': uom_unit.id,
                'uom_po_id': uom_unit.id,
                'default_code': 'SERV_DEL',
                'invoice_policy': 'delivery',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }, {
                'name': 'product_service_order',
                'categ_id': product_category.id,
                'standard_price': 40.0,
                'list_price': 90.0,
                'type': 'service',
                'uom_id': uom_hour.id,
                'uom_po_id': uom_hour.id,
                'description': 'Example of product to invoice on order',
                'default_code': 'PRE-PAID',
                'invoice_policy': 'order',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }, {
                'name': 'product_order_no',
                'categ_id': product_category.id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': uom_unit.id,
                'uom_po_id': uom_unit.id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'no',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }, {
                'name': 'product_delivery_no',
                'categ_id': product_category.id,
                'standard_price': 55.0,
                'list_price': 70.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': uom_unit.id,
                'uom_po_id': uom_unit.id,
                'default_code': 'FURN_7777',
                'invoice_policy': 'delivery',
                'expense_policy': 'no',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }
        ])

    @classmethod
    def setup_company_data(cls, company_name, **kwargs):
        return super().setup_company_data(company_name, **{
            **kwargs,
            'country_id': cls.env.ref('base.it').id,
        })

    def test_deferred_invoice(self):
        """ Create a sale order with multiple DDTs, and create an invoice with a later date.
            The export has to have the TipoDocumento TD24 for Deferred Invoice.
        """
        # Create sale order
        with freeze_time('2020-02-02 18:00'):
            self.sale_order = self.env['sale.order'].with_company(self.company).create({
                'partner_id': self.italian_partner_a.id,
                'partner_invoice_id': self.italian_partner_a.id,
                'partner_shipping_id': self.italian_partner_a.id,
                'order_line': [
                    (0, 0, {
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom_qty': 5,
                        'product_uom': product.uom_id.id,
                        'price_unit': product.list_price,
                        'tax_id': self.tax_22
                    }) for product in self.products
                ],
                'pricelist_id': self.default_pricelist.id,
                'picking_policy': 'direct',
            })
            self.sale_order.action_confirm()

            # Create two pickings, so 2 DDTs
            for dummy in range(2):
                self._create_delivery(self.sale_order, 1)

        # Create one invoice
        with freeze_time('2020-02-03 09:00'):
            deferred_invoice = self.sale_order._create_invoices()
            deferred_invoice.action_post()

        # Check the XML output of the invoice
        invoice_xml = self.edi_format._l10n_it_edi_export_invoice_as_xml(deferred_invoice)
        expected_xml = self._get_stock_ddt_test_file_content("deferred_invoice.xml")
        result = self._cleanup_etree(invoice_xml, {"//DatiGeneraliDocumento/Numero": "<Numero/>",})
        expected = self._cleanup_etree(expected_xml, {"//DatiGeneraliDocumento/Numero": "<Numero/>",})
        self.assertXmlTreeEqual(result, expected)

    def _create_delivery(self, sale_order, qty=1):
        """ Create a picking of a limited quantity and create a backorder """
        pickings = sale_order.picking_ids.filtered(lambda picking: picking.state != 'done')
        pickings.move_ids.write({'quantity_done': qty})
        wizard_action = pickings.button_validate()
        context = wizard_action['context']
        wizard = Form(self.env['stock.backorder.confirmation'].with_context(context))
        confirm_dialog = wizard.save()
        confirm_dialog.process()

    @classmethod
    def _get_stock_ddt_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_stock_ddt/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()
