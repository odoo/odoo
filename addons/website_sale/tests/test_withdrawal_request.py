# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWithdrawalRequest(WebsiteSaleCommon, HttpCase, MockEmail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.email = "john.doe@example.com"
        cls.cart.sudo().action_confirm()
        cls.order_name = cls.cart.sudo().name

    def _submit(self, order_reference, email):
        response = self.url_open(
            "/website/form/withdrawal.request",
            data={"order_reference": order_reference, "email": email},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _assert_no_withdrawal_request(self, order, order_reference, email):
        message_count = len(order.sudo().message_ids)
        with self.mock_mail_gateway():
            result = self._submit(order_reference, email)
        self.assertIn("error", result)
        self.assertNotSentEmail()
        self.assertFalse(self.env["withdrawal.request"].sudo().search([]))
        self.assertEqual(len(order.sudo().message_ids), message_count)

    def test_withdrawal_request_exact_match(self):
        with self.mock_mail_gateway():
            result = self._submit(self.order_name.lower(), self.partner.email.upper())
        self.assertTrue(result.get("id"))
        withdrawal = self.env["withdrawal.request"].sudo().browse(result["id"])
        self.assertEqual(withdrawal.order_id, self.cart)
        self.assertIn(
            self.partner.email_formatted,
            [email for mail in self._mails for email in mail["email_to"]],
        )

    def test_withdrawal_request_requires_exact_match(self):
        for order_reference, email in [
            (self.order_name[:-1] + "_", self.partner.email),
            (self.order_name[:-1] + "%", self.partner.email),
            (self.order_name[:-1] + "\\" + self.order_name[-1], self.partner.email),
            (self.order_name, "john_doe@example.com"),
            (self.order_name, "john%@example.com"),
            (self.order_name, "john.doe@example.co\\m"),
        ]:
            with self.subTest(order_reference=order_reference, email=email):
                self._assert_no_withdrawal_request(self.cart, order_reference, email)

    def test_withdrawal_request_other_company(self):
        other_company = self.env["res.company"].sudo().create({"name": "Other Company"})
        order = self._create_so(company_id=other_company.id, website_id=False).sudo()
        order.action_confirm()
        self._assert_no_withdrawal_request(order, order.name, self.partner.email)

    def test_withdrawal_request_current_website(self):
        order = self._create_so().sudo()
        order.action_confirm()
        self.assertEqual(order.website_id, self.website)
        result = self._submit(order.name, self.partner.email)
        self.assertEqual(self.env["withdrawal.request"].sudo().browse(result["id"]).order_id, order)

    def test_withdrawal_request_other_website(self):
        other_website = self.env["website"].sudo().create({"name": "Other Website"})
        order = self._create_so(website_id=other_website.id).sudo()
        order.action_confirm()
        self._assert_no_withdrawal_request(order, order.name, self.partner.email)

    def test_withdrawal_request_order_without_website(self):
        order = self._create_so(website_id=False).sudo()
        order.action_confirm()
        result = self._submit(order.name, self.partner.email)
        self.assertEqual(self.env["withdrawal.request"].sudo().browse(result["id"]).order_id, order)
