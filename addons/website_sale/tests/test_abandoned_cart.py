# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo.tests import RecordCapturer, tagged

from odoo.addons.base.tests.common import TransactionCaseWithUserPortal
from odoo.addons.mail.models.mail_template import MailTemplate


class TestWebsiteSaleCartAbandonedCommon(TransactionCaseWithUserPortal):
    def send_mail_patched(self, sale_order_id):
        email_got_sent = False

        def check_send_mail_called(this, res_id, email_values, *_args, **_kwargs):  # noqa: ARG001
            nonlocal email_got_sent
            if res_id == sale_order_id:
                email_got_sent = True

        with patch.object(MailTemplate, "send_mail", check_send_mail_called):
            self.env["website"]._send_abandoned_cart_email()
        return email_got_sent


@tagged("post_install", "-at_install")
class TestWebsiteSaleCartAbandoned(TestWebsiteSaleCartAbandonedCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        now = datetime.utcnow()
        cls.customer = cls.env["res.partner"].create({"name": "a", "email": "a@example.com"})
        cls.public_partner = cls.env["res.partner"].create({
            "name": "public",
            "email": "public@example.com",
        })
        cls.public_user = cls.env["res.users"].create({
            "name": "Foo",
            "login": "foo",
            "partner_id": cls.public_partner.id,
        })
        cls.website0 = cls.env["website"].create({
            "name": "web0",
            "cart_abandoned_delay": 1.0,  # 1 hour
        })
        cls.website1 = cls.env["website"].create({
            "name": "web1",
            "cart_abandoned_delay": 0.5,  # 30 minutes
        })
        cls.website2 = cls.env["website"].create({
            "name": "web2",
            "cart_abandoned_delay": 24.0,  # 1 day
            "user_id": cls.public_user.id,  # specific public user
        })
        product = cls.env["product.product"].create({"name": "The Product"})
        add_order_line = [
            [0, 0, {"name": "The Product", "product_id": product.id, "product_uom_qty": 1}]
        ]
        provider = cls.env["payment.provider"].create({"name": "Test", "code": "none"})
        cls.payment_method_id = (
            cls
            .env["payment.method"]
            .create({"name": "Payment method", "code": "unknown", "provider_id": provider.id})
            .id
        )
        cls.so0before = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website0.id,
            "state": "draft",
            "date_order": (now - relativedelta(hours=1)) - relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so0after = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website0.id,
            "state": "draft",
            "date_order": (now - relativedelta(hours=1)) + relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so1before = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website1.id,
            "state": "draft",
            "date_order": (now - relativedelta(minutes=30)) - relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so1after = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website1.id,
            "state": "draft",
            "date_order": (now - relativedelta(minutes=30)) + relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so2before = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website2.id,
            "state": "draft",
            "date_order": (now - relativedelta(hours=24)) - relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so2after = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "website_id": cls.website2.id,
            "state": "draft",
            "date_order": (now - relativedelta(hours=24)) + relativedelta(minutes=1),
            "order_line": add_order_line,
        })
        cls.so2before_but_public = cls.env["sale.order"].create({
            "partner_id": cls.public_partner.id,
            "website_id": cls.website2.id,
            "state": "draft",
            "date_order": (now - relativedelta(hours=24)) - relativedelta(minutes=1),
            "order_line": add_order_line,
        })

        # Must behave like so1before because public partner is not the one of website1
        cls.so1before_but_other_public = cls.env["sale.order"].create({
            "partner_id": cls.public_partner.id,
            "website_id": cls.website1.id,
            "state": "draft",
            "date_order": (now - relativedelta(minutes=30)) - relativedelta(minutes=1),
            "order_line": add_order_line,
        })

    def test_search_abandoned_cart(self):
        """Make sure the search for abandoned carts uses the delay and public partner specified in
        each website."""
        SaleOrder = self.env["sale.order"]
        abandoned = SaleOrder.search([("is_abandoned_cart", "=", True)]).ids
        self.assertTrue(self.so0before.id in abandoned)
        self.assertTrue(self.so1before.id in abandoned)
        self.assertTrue(self.so1before_but_other_public.id in abandoned)
        self.assertTrue(self.so2before.id in abandoned)
        self.assertFalse(self.so0after.id in abandoned)
        self.assertFalse(self.so1after.id in abandoned)
        self.assertFalse(self.so2after.id in abandoned)
        self.assertFalse(self.so2before_but_public.id in abandoned)

        non_abandoned = SaleOrder.search([("is_abandoned_cart", "=", False)]).ids
        self.assertFalse(self.so0before.id in non_abandoned)
        self.assertFalse(self.so1before.id in non_abandoned)
        self.assertFalse(self.so1before_but_other_public.id in non_abandoned)
        self.assertFalse(self.so2before.id in non_abandoned)
        self.assertTrue(self.so0after.id in non_abandoned)
        self.assertTrue(self.so1after.id in non_abandoned)
        self.assertTrue(self.so2after.id in non_abandoned)
        self.assertFalse(self.so2before_but_public.id in abandoned)

    def test_website_sale_abandoned_cart_email(self):
        """Make sure the send_abandoned_cart_email method sends the correct emails."""
        website = self.env.ref('base.default_website')
        website.send_abandoned_cart_email = True
        website.write({
            "send_abandoned_cart_email_activation_time": (
                datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)
            )
            - relativedelta(minutes=10)
        })

        product = self.env["product.product"].create({"name": "The Product"})
        order_line = [
            [0, 0, {"name": "The Product", "product_id": product.id, "product_uom_qty": 1}]
        ]
        abandoned_sale_order = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
        })
        self.assertTrue(abandoned_sale_order.is_abandoned_cart)
        with RecordCapturer(self.env["mail.mail"], []) as captured_mails:
            self.env["website"]._send_abandoned_cart_email()
            # Currently the class init level sales orders might be created in the time window
            # of the abandoned delay configured on the website, thus interfering here.
            # Without modifying the whole legacy test, we filter the captured records based on
            # res_id, so that other SOs don't interfere with this test case
            abandoned_sale_order_mails = captured_mails.records.filtered(
                lambda rec: rec.res_id == abandoned_sale_order.id and rec.model == "sale.order"
            )
            self.assertEqual(
                len(abandoned_sale_order_mails), 1, "more than one email for abandoned cart sent"
            )
            # since saas-18.1, the default email template for abandoned carts uses
            # use_default_to == True thus it should not create an explicit email_to value but use
            # partner_ids
            self.assertFalse(abandoned_sale_order_mails["email_to"])
            self.assertEqual(abandoned_sale_order_mails["partner_ids"].id, self.customer.id)

        # Test that no mail is sent if the partner has no email address.
        self.customer.email = False
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
        })
        self.assertFalse(self.send_mail_patched(abandoned_sale_order.id))

        # Test that no mail is sent if the recovery email of the sale order has already been sent.
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
            "cart_recovery_email_sent": True,
        })
        self.assertFalse(self.send_mail_patched(abandoned_sale_order.id))

        # Test that no email is sent if the sale order contains product that are free.
        free_product_template = self.env["product.template"].create({
            "list_price": 0.0,
            "name": "free_product",
        })
        free_product_product = free_product_template.product_variant_id
        order_line = [
            [
                0,
                0,
                {
                    "name": "The Product",
                    "product_id": free_product_product.id,
                    "product_uom_qty": 1,
                },
            ]
        ]
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
        })
        self.assertFalse(self.send_mail_patched(abandoned_sale_order.id))

        # Test that no email is sent if the sale order has no error in its transaction.
        abandoned_sale_order = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
        })
        transaction = self.env["payment.transaction"].create({
            "provider_id": self.ref("payment.payment_provider_demo"),
            "payment_method_id": self.payment_method_id,
            "partner_id": self.customer.id,
            "reference": abandoned_sale_order.name,
            "amount": abandoned_sale_order.amount_total,
            "state": "error",
            "currency_id": self.env.ref("base.EUR").id,
        })
        abandoned_sale_order.transaction_ids += transaction
        self.assertFalse(self.send_mail_patched(abandoned_sale_order.id))

        # Test that if the partner of the abandoned cart made an order ulterior to the abandoned
        # cart create date, no email is sent.
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay))
            - relativedelta(minutes=1),
            "order_line": order_line,
        })
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "website_id": website.id,
            "state": "draft",
            "date_order": datetime.utcnow(),
            "order_line": order_line,
        })
        self.assertFalse(self.send_mail_patched(abandoned_sale_order.id))
