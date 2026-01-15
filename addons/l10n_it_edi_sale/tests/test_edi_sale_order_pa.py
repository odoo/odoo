import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiSaleOrderPa(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist = cls.env['product.pricelist'].with_company(cls.company).create({
            'name': 'EUR pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': False,
        })

        cls.module = 'l10n_it_edi_sale'
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')

    def get_sales_order_vals(self, **kwargs):
        return {
            'company_id': self.company.id,
            'partner_id': self.italian_partner_b.id,
            'pricelist_id': self.pricelist.id,
            **kwargs,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'product_uom_qty': 1,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        }

    def create_sale_order_and_invoice(self, sale_order_vals):
        order = self.env['sale.order'].create(sale_order_vals)
        order.action_confirm()
        invoice = order._create_invoices()
        invoice.action_post()
        return invoice

    def test_invoice_from_sale_order_pa_partner_no_origin_fields(self):
        """ Tests that CUP and CIG from the sales order are passed to invoice.
            As the origin_document fields are not filled in the SO, but CUP/CIG are,
            origin_document fields in invoice are filled according to the Sales Order.
        """
        sale_order_vals = self.get_sales_order_vals(
            name='Test Sale Order 1',
            l10n_it_cup='0123456789',
            l10n_it_cig='0987654321',
        )
        with freeze_time("2024-03-01"):
            invoice = self.create_sale_order_and_invoice(sale_order_vals)
        self.assertRecordValues(invoice, [{
            'l10n_it_cup': '0123456789',
            'l10n_it_cig': '0987654321',
            'l10n_it_origin_document_name': 'Test Sale Order 1',
            'l10n_it_origin_document_type': 'purchase_order',
            'l10n_it_origin_document_date': datetime.date(2024, 3, 1),
        }])

    def test_invoice_from_sale_order_pa_partner_with_origin_fields(self):
        """ Tests that, if at least one of the origin_documents fields is filled in the Sales Order,
            only those values are passed to the invoice (no default values taken from the SO are used,
            like the SO date). CUP and/or CIG filled in the Sales Order are passed to the invoice.
        """
        sale_order_vals = self.get_sales_order_vals(
            l10n_it_cup='0123456789',
            l10n_it_origin_document_type='contract',
            l10n_it_origin_document_date=datetime.date(2024, 2, 23),
        )
        with freeze_time("2024-03-02"):
            invoice = self.create_sale_order_and_invoice(sale_order_vals)
        self.assertRecordValues(invoice, [{
            'l10n_it_cup': '0123456789',
            'l10n_it_cig': None,
            'l10n_it_origin_document_name': None,
            'l10n_it_origin_document_type': 'contract',
            'l10n_it_origin_document_date': datetime.date(2024, 2, 23),
        }])

    def test_invoice_from_sale_order_pa_partner_no_pa_fields(self):
        """ As none of the PA fields (origin_documents, CUP, CIG) are filled, the origin_document
            fields should not be automatically filled with the Sales Order values.
        """
        with freeze_time("2024-03-03"):
            invoice = self.create_sale_order_and_invoice(self.get_sales_order_vals())
        self.assertRecordValues(invoice, [{
            'l10n_it_cig': None,
            'l10n_it_cup': None,
            'l10n_it_origin_document_name': None,
            'l10n_it_origin_document_type': None,
            'l10n_it_origin_document_date': None,
        }])

