import json
import re
from datetime import datetime
from unittest.mock import patch

from lxml import html

import odoo

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestPoSController(TestPointOfSaleHttpCommon):
    def _pay_pos_order(self, order, amount=10.0):
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        self.env["pos.make.payment"].with_context(**payment_context).create(
            {
                "amount": amount,
                "payment_method_id": self.main_pos_config.payment_method_ids[0].id,
            }
        ).with_context(**payment_context).action_make_payment()
        return order

    def test_qr_code_receipt(self):
        self.authenticate(None, None)
        self.new_partner = self.env["res.partner"].create(
            {
                "name": "AAA Partner",
                "zip": "12345",
                "state_id": self.env.ref("base.state_us_1").id,
                "country_id": self.env.ref("base.us").id,
            }
        )
        self.product1 = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "is_storable": True,
                "list_price": 10.0,
                "taxes_id": False,
            }
        )
        self.main_pos_config.open_ui()
        self.pos_order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "session_id": self.main_pos_config.current_session_id.id,
                "partner_id": self.new_partner.id,
                "access_token": "1234567890",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product1.id,
                            "price_unit": 10,
                            "discount": 0.0,
                            "qty": 1.0,
                            "tax_ids": False,
                            "price_subtotal": 10,
                            "price_subtotal_incl": 10,
                        },
                    )
                ],
                "amount_tax": 10,
                "amount_total": 10,
                "amount_paid": 10.0,
                "amount_return": 10.0,
            }
        )
        self._pay_pos_order(self.pos_order)
        self.main_pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            "access_token": self.pos_order.access_token,
            "name": self.new_partner.name,
            "email": "test@test.com",
            "company_name": self.new_partner.commercial_company_name,
            "vat": self.new_partner.vat,
            "street": "Test street",
            "city": "Test City",
            "zipcode": self.new_partner.zip,
            "country_id": self.new_partner.country_id.id,
            "state_id": self.new_partner.state_id.id,
            "phone": "123456789",
            "csrf_token": odoo.http.Request.csrf_token(self),
        }
        self.url_open(
            f"/pos/ticket/validate?access_token={self.pos_order.access_token}",
            data=get_invoice_data,
        )
        self.assertEqual(
            self.env["res.partner"].sudo().search_count([("name", "=", "AAA Partner")]),
            1,
        )
        self.assertTrue(
            self.pos_order.is_invoiced, "The pos order should have an invoice"
        )
        self.assertTrue(
            len(self.pos_order.pos_reference) >= 12,
            "The pos reference should not be less than 12 characters",
        )

    def test_qr_code_receipt_user_connected(self):
        self.partner_1 = self.env["res.partner"].create(
            {
                "name": "Valid Lelitre",
                "email": "valid.lelitre@agrolait.com",
            }
        )
        self.partner_1_user = mail_new_test_user(
            self.env,
            name=self.partner_1.name,
            login="partner_1",
            email=self.partner_1.email,
            groups="base.group_portal",
        )
        self.authenticate("partner_1", "partner_1")

        self.product1 = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "is_storable": True,
                "list_price": 10.0,
                "taxes_id": False,
            }
        )
        self.main_pos_config.open_ui()
        self.pos_order = self.env["pos.order"].create(
            {
                "session_id": self.main_pos_config.current_session_id.id,
                "company_id": self.env.company.id,
                "access_token": "1234567890",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product1.id,
                            "price_unit": 10,
                            "discount": 0.0,
                            "qty": 1.0,
                            "tax_ids": False,
                            "price_subtotal": 10,
                            "price_subtotal_incl": 10,
                        },
                    )
                ],
                "amount_tax": 10,
                "amount_total": 10,
                "amount_paid": 10.0,
                "amount_return": 10.0,
            }
        )
        self._pay_pos_order(self.pos_order)
        self.main_pos_config.current_session_id.close_session_from_ui()
        res = self.url_open(
            f"/pos/ticket/validate?access_token={self.pos_order.access_token}",
            timeout=30000,
        )
        self.assertTrue(
            self.pos_order.is_invoiced, "The pos order should have an invoice"
        )
        self.assertTrue("my/invoices" in res.url)

    def test_qr_code_receipt_user_not_connected(self):

        self.product1 = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "is_storable": True,
                "list_price": 10.0,
                "taxes_id": False,
            }
        )
        self.main_pos_config.open_ui()
        self.pos_order = self.env["pos.order"].create(
            {
                "session_id": self.main_pos_config.current_session_id.id,
                "company_id": self.env.company.id,
                "access_token": "1234567890",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Product 1",
                            "product_id": self.product1.id,
                            "price_unit": 10,
                            "tax_ids": False,
                            "price_subtotal": 10,
                            "price_subtotal_incl": 10,
                        },
                    )
                ],
                "amount_tax": 10,
                "amount_total": 10,
                "amount_paid": 10.0,
                "amount_return": 10.0,
                "pos_reference": "2500-002-00002",
                "ticket_code": "inPoS",
                "date_order": datetime.today(),
            }
        )
        context_make_payment = {
            "active_ids": [self.pos_order.id],
            "active_id": self.pos_order.id,
        }
        self.pos_make_payment = (
            self.env["pos.make.payment"]
            .with_context(context_make_payment)
            .create(
                {
                    "amount": 10.0,
                    "payment_method_id": self.main_pos_config.payment_method_ids[0].id,
                }
            )
        )
        context_payment = {"active_id": self.pos_order.id}
        self.pos_make_payment.with_context(context_payment).action_make_payment()
        self.main_pos_config.current_session_id.close_session_from_ui()
        self.start_tour("/pos/ticket", "invoicePoSOrderWithSelfInvocing", login=None)
        self.assertTrue(
            self.pos_order.account_move,
            "The pos order should have an invoice after self invoicing",
        )

    def test_qr_code_receipt_user_updated(self):
        self.authenticate(None, None)
        self.partner_1 = self.env["res.partner"].create(
            {
                "name": "Valid Lelitre",
                "email": "valid.lelitre@agrolait.com",
            }
        )

        self.product1 = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "is_storable": True,
                "list_price": 10.0,
                "taxes_id": False,
            }
        )
        self.main_pos_config.open_ui()
        self.pos_order = self.env["pos.order"].create(
            {
                "session_id": self.main_pos_config.current_session_id.id,
                "company_id": self.env.company.id,
                "partner_id": self.partner_1.id,
                "access_token": "1234567890",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product1.id,
                            "price_unit": 10,
                            "discount": 0.0,
                            "qty": 1.0,
                            "tax_ids": False,
                            "price_subtotal": 10,
                            "price_subtotal_incl": 10,
                        },
                    )
                ],
                "amount_tax": 10,
                "amount_total": 10,
                "amount_paid": 10.0,
                "amount_return": 10.0,
            }
        )
        self._pay_pos_order(self.pos_order)
        self.main_pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            "access_token": self.pos_order.access_token,
            "name": "New Name",
            "email": "test@test.com",
            "vat": "VAT_TEST_NUMBER_123",
            "street": "Test street",
            "city": "Test City",
            "zipcode": "12345",
            "country_id": self.company.country_id.id,
            "phone": "123456789",
            "state_id": self.company.country_id.state_ids[:1].id,
            "csrf_token": odoo.http.Request.csrf_token(self),
        }
        self.url_open(
            f"/pos/ticket/validate?access_token={self.pos_order.access_token}",
            data=get_invoice_data,
            timeout=30000,
        )
        self.assertEqual(self.partner_1.vat, "VAT_TEST_NUMBER_123")
        self.assertEqual(self.partner_1.name, "New Name")
        self.assertEqual(self.partner_1.zip, "12345")


@odoo.tests.tagged("post_install", "-at_install")
class TestPoSControllerInput(TestPointOfSaleHttpCommon):
    def _create_ticket_order(self, reference):
        self.main_pos_config.open_ui()
        return self.env["pos.order"].create(
            {
                "session_id": self.main_pos_config.current_session_id.id,
                "pos_reference": reference,
                "ticket_code": "abcde",
                "date_order": "2026-01-15 12:00:00",
                "amount_tax": 0,
                "amount_total": 0,
                "amount_paid": 0,
                "amount_return": 0,
            }
        )

    def _post_ticket_form(self, **values):
        page = self.url_open("/pos/ticket")
        token = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
        self.assertTrue(token, "the ticket form must carry a CSRF token")
        return self.url_open(
            "/pos/ticket",
            data={"csrf_token": token.group(1), **values},
            allow_redirects=False,
        )

    def test_ticket_form_rejects_a_malformed_date(self):
        res = self._post_ticket_form(
            pos_reference="123456789012",
            date_order="not-a-date",
            ticket_code="abcde",
        )
        self.assertEqual(res.status_code, 200)

    def test_ticket_form_rejects_a_date_with_too_many_parts(self):
        res = self._post_ticket_form(
            pos_reference="123456789012",
            date_order="2026-1-1-1-1-1-1-1",
            ticket_code="abcde",
        )
        self.assertEqual(res.status_code, 200)

    def test_ticket_form_rejects_an_impossible_date(self):
        res = self._post_ticket_form(
            pos_reference="123456789012",
            date_order="2026-02-31",
            ticket_code="abcde",
        )
        self.assertEqual(res.status_code, 200)

    def test_ticket_form_rejects_dates_outside_lookup_range(self):
        for date_order in ("0001-01-01", "9999-12-30", "9999-12-31"):
            with self.subTest(date_order=date_order):
                res = self._post_ticket_form(
                    pos_reference="123456789012",
                    date_order=date_order,
                    ticket_code="abcde",
                )
                self.assertEqual(res.status_code, 200)
                self.assertIn("Please fill all the required fields", res.text)

    def test_ticket_reference_length_excludes_surrounding_whitespace(self):
        res = self._post_ticket_form(
            pos_reference="           1", date_order="2026-01-15", ticket_code="abcde"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("at least 12 characters", res.text)

    def test_ticket_lookup_treats_pattern_characters_literally(self):
        reference = r"Ticket 12345678\_%"
        order = self._create_ticket_order(reference)
        res = self._post_ticket_form(
            pos_reference=reference,
            date_order="2026-01-15",
            ticket_code=order.ticket_code,
        )
        self.assertEqual(res.status_code, 303)
        self.assertEqual(
            res.headers["Location"],
            f"/pos/ticket/validate?access_token={order.access_token}",
        )

    def test_ticket_uuid_redirect(self):
        order = self._create_ticket_order("Ticket 123456789012")
        res = self.url_open(
            f"/pos/ticket?order_uuid={order.uuid}", allow_redirects=False
        )
        self.assertEqual(res.status_code, 303)
        self.assertEqual(
            res.headers["Location"],
            f"/pos/ticket/validate?access_token={order.access_token}",
        )

    def test_ticket_lookup_cannot_expand_an_escaped_underscore(self):
        order = self._create_ticket_order(r"Ticket 12345678\x%")
        res = self._post_ticket_form(
            pos_reference=r"Ticket 12345678\_%",
            date_order="2026-01-15",
            ticket_code=order.ticket_code,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("No sale order found", res.text)

    def test_customer_display_rejects_missing_configs(self):
        for config_id in ("not-a-number", "0", "-1", "2147483647"):
            with self.subTest(config_id=config_id):
                res = self.url_open(
                    f"/pos_customer_display/{config_id}/test-device?access_token=invalid"
                )
                self.assertEqual(res.status_code, 404)

    def test_customer_display_requires_token_and_session(self):
        url = f"/pos_customer_display/{self.main_pos_config.id}/test-device"
        res = self.url_open(f"{url}?access_token={self.main_pos_config.access_token}")
        self.assertEqual(res.status_code, 404)
        self.main_pos_config.open_ui()
        for suffix in ("", "?access_token=invalid", "?access_token=%C3%A9"):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.url_open(url + suffix).status_code, 404)
        res = self.url_open(f"{url}?access_token={self.main_pos_config.access_token}")
        self.assertEqual(res.status_code, 200)

    def test_pos_ui_resumes_another_cashiers_session(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.authenticate("pos_admin", "pos_admin")
        res = self.url_open(f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.main_pos_config.current_session_id, session)

    def test_pos_ui_rejects_closing_session(self):
        self.main_pos_config.open_ui()
        self.main_pos_config.current_session_id.state = "closing_control"
        self.authenticate("pos_admin", "pos_admin")
        res = self.url_open(f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False)
        self.assertEqual(res.status_code, 303)

    def test_pos_ui_foreign_company_cannot_open_a_session(self):
        elsewhere = self.env["res.company"].create({"name": "Foreign POS user company"})
        outsider = mail_new_test_user(
            self.env,
            login="pos_foreign_opener",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=elsewhere.id,
            company_ids=[odoo.fields.Command.set(elsewhere.ids)],
        )
        self.assertFalse(self.main_pos_config.session_ids)
        self.authenticate(outsider.login, outsider.login)
        res = self.url_open(f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertFalse(self.main_pos_config.session_ids)

    def test_pos_ui_uses_authorized_config_company(self):
        elsewhere = self.env["res.company"].create({"name": "Other default company"})
        cashier = mail_new_test_user(
            self.env,
            login="pos_multiple_companies",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=elsewhere.id,
            company_ids=[
                odoo.fields.Command.set(
                    (elsewhere | self.main_pos_config.company_id).ids
                )
            ],
        )
        self.authenticate(cashier.login, cashier.login)
        res = self.url_open(f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False)
        self.assertEqual(res.status_code, 200)
        session = self.main_pos_config.current_session_id
        self.assertEqual(session.company_id, self.main_pos_config.company_id)
        self.assertEqual(session.user_id, cashier)

    def test_pos_ui_rolls_back_a_competing_session_creation(self):
        def open_competing_sessions(config):
            config.env["res.partner"].create({"name": "Rolled back POS opener"})
            sessions = config.env["pos.session"].with_context(onboarding_creation=True)
            sessions.create({"config_id": config.id})
            sessions.create({"config_id": config.id})

        self.authenticate("pos_user", "pos_user")
        with patch.object(
            type(self.main_pos_config), "open_ui", open_competing_sessions
        ):
            res = self.url_open(
                f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False
            )
        self.assertEqual(res.status_code, 303)
        self.assertFalse(self.main_pos_config.session_ids)
        self.assertFalse(
            self.env["res.partner"].search_count(
                [("name", "=", "Rolled back POS opener")]
            )
        )

    def test_pos_ui_refuses_rescue_only_config(self):
        self.main_pos_config.open_ui()
        self.main_pos_config.current_session_id.rescue = True
        self.assertFalse(self.main_pos_config.current_session_id)
        self.authenticate("pos_user", "pos_user")
        res = self.url_open(f"/pos/ui/{self.main_pos_config.id}", allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertEqual(len(self.main_pos_config.session_ids), 1)

    def test_pos_ui_missing_or_archived_config_cannot_open_session(self):
        self.main_pos_config.active = False
        self.authenticate("pos_user", "pos_user")
        for path in (
            "/pos/ui",
            "/pos/web",
            "/pos/ui/0",
            "/pos/ui/-1",
            f"/pos/ui/{self.main_pos_config.id}",
        ):
            with self.subTest(path=path):
                res = self.url_open(path, allow_redirects=False)
                self.assertEqual(res.status_code, 303)
        self.assertFalse(self.main_pos_config.session_ids)

    def test_ticket_validation_rejects_client_template_state_over_http(self):
        self.authenticate(None, None)
        order = self._create_ticket_order("Ticket 123456789012")
        order.state = "paid"
        res = self.url_open(
            f"/pos/ticket/validate?access_token={order.access_token}",
            data={
                "csrf_token": odoo.http.Request.csrf_token(self),
                "name": "Invoice customer",
                "extra_field_values": "untrusted",
                "invalid_fields": "untrusted",
                "messages": "untrusted",
                "pos_order": "untrusted",
                "partner_sudo": "untrusted",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(order.account_move)

    def test_invalid_ticket_address_preserves_submitted_values(self):
        self.authenticate(None, None)
        order = self._create_ticket_order("Ticket 123456789012")
        order.state = "paid"
        country = self.env.ref("base.ca")
        state = self.env["res.country.state"].search(
            [("country_id", "=", country.id)], limit=1
        )
        submitted = {
            "name": "Customer <entered>",
            "email": "invalid-email",
            "street": "New street",
            "street2": "",
            "city": "New city",
            "zip": "K1A 0B1",
            "phone": "123456789",
            "country_id": str(country.id),
            "state_id": str(state.id),
        }
        response = self.url_open(
            f"/pos/ticket/validate?access_token={order.access_token}",
            data={"csrf_token": odoo.http.Request.csrf_token(self), **submitted},
        )
        self.assertEqual(response.status_code, 200)
        document = html.fromstring(response.content)
        for name, value in submitted.items():
            with self.subTest(name=name):
                if name in ("country_id", "state_id"):
                    selected = document.xpath(
                        f"//select[@name='{name}']/option[@selected]/@value"
                    )
                    self.assertEqual(selected, [value])
                else:
                    self.assertEqual(
                        document.xpath(f"//input[@name='{name}']/@value"), [value]
                    )
        self.assertFalse(order.account_move)
        self.assertFalse(order.partner_id)

    def test_malformed_ticket_address_relations_render_errors(self):
        self.authenticate(None, None)
        order = self._create_ticket_order("Ticket 123456789012")
        order.state = "paid"
        response = self.url_open(
            f"/pos/ticket/validate?access_token={order.access_token}",
            data={
                "csrf_token": odoo.http.Request.csrf_token(self),
                "country_id": "not-a-country",
                "state_id": "not-a-state",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Please select a valid value", response.text)
        self.assertFalse(order.account_move)

    def test_ticket_address_relation_values_are_normalized(self):
        self.authenticate(None, None)
        order = self._create_ticket_order("Ticket 123456789012")
        order.state = "paid"
        country = self.env.ref("base.us")
        state = self.env.ref("base.state_us_1")
        response = self.url_open(
            f"/pos/ticket/validate?access_token={order.access_token}",
            data={
                "csrf_token": odoo.http.Request.csrf_token(self),
                "name": "Customer",
                "email": "invalid-email",
                "country_id": f"+{country.id}",
                "state_id": f"00{state.id}",
            },
        )
        self.assertEqual(response.status_code, 200)
        document = html.fromstring(response.content)
        for name, record in (("country_id", country), ("state_id", state)):
            self.assertEqual(
                document.xpath(f"//select[@name='{name}']/option[@selected]/@value"),
                [str(record.id)],
            )
        self.assertFalse(order.account_move)

    def test_ticket_form_accepts_a_well_formed_date(self):
        res = self._post_ticket_form(
            pos_reference="123456789012",
            date_order="2026-01-15",
            ticket_code="abcde",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("No sale order found", res.text)

    def test_pos_ui_rejects_a_non_numeric_config_id(self):
        self.authenticate("admin", "admin")
        res = self.url_open("/pos/ui/not-a-number", allow_redirects=False)
        self.assertEqual(res.status_code, 404)

    def test_pos_ui_accepts_a_numeric_config_id(self):
        self.authenticate("pos_user", "pos_user")
        res = self.url_open(
            "/pos/ui/%d" % self.main_pos_config.id, allow_redirects=False
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Cache-Control"], "no-store")

    def test_pos_boot_and_printer_use_boolean_values(self):
        self.authenticate("pos_user", "pos_user")
        for value, expected in (("False", False), ("0", False), ("true", True)):
            with self.subTest(value=value):
                self.env["ir.config_parameter"].sudo().set_param(
                    "point_of_sale.use_lna", value
                )
                res = self.url_open(
                    f"/pos/ui/{self.main_pos_config.id}?from_backend={value}&tours={value}",
                    allow_redirects=False,
                )
                self.assertEqual(res.status_code, 200)
                match = re.search(r"var odoo = (\{.*?\});", res.text, re.DOTALL)
                self.assertTrue(match, "POS page must contain its boot payload")
                boot = json.loads(match.group(1))
                self.assertEqual(boot["from_backend"], int(expected))
                self.assertEqual(boot["use_pos_fake_tours"], expected)
                self.assertEqual(boot["use_lna"], expected)
                self.assertEqual(
                    self.env["pos.printer"].use_local_network_access(),
                    {"use_lna": expected},
                )

    def test_pos_ui_on_a_foreign_company_redirects(self):
        elsewhere = self.env["res.company"].create({"name": "Elsewhere Co"})
        outsider = mail_new_test_user(
            self.env,
            login="pos_elsewhere_user",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=elsewhere.id,
            company_ids=[odoo.fields.Command.set(elsewhere.ids)],
        )
        self.main_pos_config.open_ui()
        self.authenticate(outsider.login, outsider.login)
        res = self.url_open(
            "/pos/ui/%d" % self.main_pos_config.id, allow_redirects=False
        )
        self.assertNotEqual(res.status_code, 500)
