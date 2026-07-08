# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged("post_install", "-at_install")
class TestSaleAutoInvoice(TestSaleCouponCommon):
    def test_automatic_invoice_on_zero_amount_order(self):
        self.env.company.sale_automatic_invoice = True
        # Create a loyalty program with 100% discount
        self.env["loyalty.program"].sudo().create({
            "name": "100discount",
            "program_type": "promo_code",
            "rule_ids": [Command.create({"code": "100dis", "minimum_amount": 0})],
            "reward_ids": [Command.create({"discount": 100})],
        })
        # Add order line to order
        order = self._create_so(
            order_line=[
                Command.create({
                    "product_id": self.product_A.id,
                    "product_uom_qty": 1,
                    "price_unit": 200,
                })
            ]
        )
        # Apply discount
        self._apply_promo_code(order, "100dis")
        order._validate_order()
        self.assertTrue(
            order.invoice_ids, "Invoices should be generated for orders with zero total amount"
        )

    def test_automatic_invoice_email_on_zero_amount_order(self):
        self.env.company.sale_automatic_invoice = True

        # Create a loyalty program with 100% discount
        self.env['loyalty.program'].sudo().create({
            'name': '100discount',
            'program_type': 'promo_code',
            'rule_ids': [
                Command.create({
                    'code': "100dis",
                    'minimum_amount': 0,
                })
            ],
            'reward_ids': [
                Command.create({
                    'discount': 100,
                }),
            ],
        })

        # Create order
        order = self._create_so(
            order_line=[
                Command.create({
                    'product_id': self.product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 200,
                })
            ]
        )

        # Create a dummy mail template for the invoice
        mail_template = self.env['mail.template'].create({
            'name': 'Test Invoice Template',
            'model_id': self.env.ref('account.model_account_move').id,
            'auto_delete': False,
        })
        self.env['ir.config_parameter'].sudo().set_int('sale.default_invoice_email_template', mail_template.id)

        # Ensure partner has an email address
        order.partner_id.email = "test@example.com"

        # Apply discount
        self._apply_promo_code(order, '100dis')

        order._validate_order()

        self.assertTrue(
            order.invoice_ids.is_move_sent,
            "Invoice should be marked as sent",
        )

        emails = self.env['mail.mail'].search([])
        self.assertTrue(
            emails,
            "An email should have been generated for the invoice",
        )
