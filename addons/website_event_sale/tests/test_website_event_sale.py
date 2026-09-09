from unittest.mock import patch

from odoo import http
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


class TestWebsiteEventSale(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):
    def test_website_event_sale_free_tickets(self):
        self.authenticate(None, None)
        free_ticket = self.env["event.event.ticket"].create(
            {
                "event_id": self.event.id,
                "name": "Free",
                "product_id": self.product_event.id,
                "price": 0,
            }
        )
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == "name")
        email_question = event_questions.filtered(lambda q: q.question_type == "email")
        phone_question = event_questions.filtered(lambda q: q.question_type == "phone")
        existing_so = self.env["sale.order"].search([])
        self.url_open(
            f"/event/{self.event.id}/registration/confirm",
            data={
                f"1-name-{name_question.id}": "Bob",
                f"1-email-{email_question.id}": "bob@test.lan",
                f"1-phone-{phone_question.id}": "8989898989",
                "1-event_ticket_id": free_ticket.id,
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(
            self.env["sale.order"].search([]),
            existing_so,
            "Sale order should not be created for the free tickets",
        )
        self.assertEqual(len(self.event.registration_ids), event_registration_count + 1)

    def test_website_event_sale_free_paid_mix(self):
        self.authenticate(None, None)
        free_ticket = self.env["event.event.ticket"].create(
            {
                "event_id": self.event.id,
                "name": "Free",
                "product_id": self.product_event.id,
                "price": 0,
            }
        )
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == "name")
        email_question = event_questions.filtered(lambda q: q.question_type == "email")
        phone_question = event_questions.filtered(lambda q: q.question_type == "phone")
        self.url_open(
            f"/event/{self.event.id}/registration/confirm",
            data={
                f"1-name-{name_question.id}": "Bob",
                f"1-email-{email_question.id}": "bob@test.lan",
                f"1-phone-{phone_question.id}": "8989898989",
                "1-event_ticket_id": self.ticket.id,
                f"2-name-{name_question.id}": "joe",
                f"2-email-{email_question.id}": "joe@test.lan",
                f"2-phone-{phone_question.id}": "8989898988",
                "2-event_ticket_id": free_ticket.id,
                "csrf_token": http.Request.csrf_token(self),
            },
        )

        self.assertEqual(len(self.event.registration_ids), event_registration_count + 2)
        self.assertTrue(
            self.env["sale.order"].search(
                [
                    ("line_ids.event_ticket_id", "=", self.ticket.id),
                    ("line_ids.event_ticket_id", "=", free_ticket.id),
                ]
            ),
            "Sale order should be created for the free/paid tickets mix",
        )


@tagged("post_install", "-at_install")
class TestRegistrationSaleBranches(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):
    def _questions(self):
        qs = self.event.question_ids
        return {
            f"1-name-{qs.filtered(lambda q: q.question_type == 'name').id}": "Zoe",
            f"1-email-{qs.filtered(lambda q: q.question_type == 'email').id}": "zoe@example.com",
            f"1-phone-{qs.filtered(lambda q: q.question_type == 'phone').id}": "5550001111",
        }

    def test_zero_total_order_autoconfirms(self):
        free_product = self.env["product.product"].create(
            {
                "type": "service",
                "service_tracking": "event",
                "list_price": 0,
                "name": "Free event seat",
                "taxes_id": [Command.set(self.zero_tax.ids)],
            }
        )
        free_ticket = self.env["event.event.ticket"].create(
            {
                "event_id": self.event.id,
                "name": "Free with cart",
                "product_id": free_product.id,
                "price": 0,
            }
        )
        freebie = self.env["product.product"].create(
            {
                "name": "Zero-cost goodie",
                "type": "consu",
                "list_price": 0,
                "sale_ok": True,
                "website_published": True,
            }
        )
        self.authenticate(None, None)
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "product_template_id": freebie.product_tmpl_id.id,
                "product_id": freebie.id,
                "quantity": 1,
            },
        }
        res = self.opener.post(
            self.base_url() + "/shop/cart/add",
            json=payload,
        )
        self.assertEqual(res.status_code, 200)

        res = self.url_open(
            f"/event/{self.event.id}/registration/confirm",
            data={
                **self._questions(),
                "1-event_ticket_id": free_ticket.id,
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertIn("/shop/confirmation", res.url)
        order = self.env["sale.order"].search(
            [("line_ids.event_ticket_id", "=", free_ticket.id)],
        )
        self.assertEqual(len(order), 1)
        self.assertEqual(order.amount_total, 0)
        self.assertEqual(order.state, "done")

    def test_registration_confirm_parses_the_form_once(self):
        """The POST must be parsed once, not once by the parent and once here."""
        self.authenticate(None, None)
        calls = []
        original = WebsiteEventController._process_attendees_form

        def counting(controller, event, form_details):
            calls.append(event.id)
            return original(controller, event, form_details)

        with patch.object(WebsiteEventController, "_process_attendees_form", counting):
            res = self.url_open(
                f"/event/{self.event.id}/registration/confirm",
                data={
                    **self._questions(),
                    "1-event_ticket_id": self.ticket.id,
                    "csrf_token": http.Request.csrf_token(self),
                },
            )

        self.assertEqual(res.status_code, 200)
        self.assertIn("/shop/", res.url)
        self.assertEqual(
            len(calls), 1, "the posted form was parsed more than once: %s" % calls
        )

    def test_registration_confirm_keeps_the_parent_error_redirect(self):
        """A POST the parent rejects still answers with the parent's redirect."""
        self.authenticate(None, None)
        res = self.url_open(
            f"/event/{self.event.id}/registration/confirm",
            data={
                **self._questions(),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertIn("registration_error_code=missing_ticket", res.url)
