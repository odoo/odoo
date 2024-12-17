# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nECAccountSale(TestSaleCommon):

    @classmethod
    @TestSaleCommon.setup_country('ec')
    def setUpClass(cls):
        super().setUpClass()
        cls.sri_payment_method = cls.env['l10n_ec.sri.payment'].create({
            'name': 'new sri',
            'active': True,
            'code': 'new',
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': cls.company_data['product_order_no'].id,
                    'product_uom_qty': 5,
                    'tax_ids': False,
                }),
            ]
        })

        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }

    def test_create_sale_order_with_default_sri_payment(self):
        first_sri_payment_method = self.env['l10n_ec.sri.payment'].search([], limit=1)

        self.assertEqual(self.sale_order.l10n_ec_sri_payment_id, first_sri_payment_method)

        # Set sri payment method with sequence less than first one
        self.sri_payment_method.sequence = first_sri_payment_method.sequence - 1

        new_sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })
        self.assertEqual(new_sale_order.l10n_ec_sri_payment_id, self.sri_payment_method)

    def test_propagate_sri_payment_to_invoice(self):
        self.sale_order.l10n_ec_sri_payment_id = self.sri_payment_method.id
        self.sale_order.action_confirm()
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered',
        })
        payment.create_invoices()
        invoice = self.sale_order.invoice_ids
        self.assertEqual(self.sale_order.l10n_ec_sri_payment_id, invoice.l10n_ec_sri_payment_id)
