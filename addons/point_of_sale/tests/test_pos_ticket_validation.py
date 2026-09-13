import logging
from types import SimpleNamespace
from unittest.mock import patch

from lxml import html

from odoo.fields import Command
from odoo.http import Response
from odoo.tests import tagged

from odoo.addons.point_of_sale.controllers import main
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_pos_invoice_guards import TestPosInvoiceGuards
from odoo.addons.portal.controllers import portal

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosTicketValidation(TestPoSCommon):
    _make_order = TestPosInvoiceGuards._make_order

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("Ticket product", self.categ_basic, 100, 50)
        self._start_pos_session(self.cash_pm1, 0)
        self.partner = self.env.user.partner_id
        self.partner.write(
            {
                "name": "Invoice customer",
                "email": "customer@example.test",
                "street": "Test street",
                "city": "Test city",
                "zip": "10001",
                "country_id": self.env.ref("base.us").id,
                "state_id": self.env.ref("base.state_us_1").id,
                "function": "Buyer",
                "phone_ids": [Command.create({"number": "5555555555"})],
            }
        )
        self.order = self._make_order("draft")
        self.order.add_payment(
            {
                "pos_order_id": self.order.id,
                "amount": 100,
                "payment_method_id": self.cash_pm1.id,
            }
        )
        self.order.action_pos_order_paid()

    def _submit_ticket(self, method="POST", field_names=None, **values):
        fake_request = SimpleNamespace(
            env=self.env,
            httprequest=SimpleNamespace(method=method),
            redirect=lambda url: ("redirect", url),
            render=lambda template, context: ("render", template, context),
            prepare_response=Response,
        )
        partner_field, invoice_field = field_names or (
            "function",
            "invoice_source_email",
        )
        invoice_fields = self.env["ir.model.fields"]._get("account.move", invoice_field)
        partner_fields = self.env["ir.model.fields"]._get("res.partner", partner_field)
        endpoint = main.PosController.show_ticket_validation_screen
        while hasattr(endpoint, "__wrapped__"):
            endpoint = endpoint.__wrapped__
        with (
            patch.object(main, "request", fake_request),
            patch.object(portal, "request", fake_request),
            patch.object(
                type(self.env["account.move"]),
                "get_invoice_localisation_fields_required_to_invoice",
                return_value=list(invoice_fields),
            ),
            patch.object(
                type(self.env["res.partner"]),
                "get_partner_localisation_fields_required_to_invoice",
                return_value=list(partner_fields),
            ),
        ):
            return endpoint(
                main.PosController(), access_token=self.order.access_token, **values
            )

    def test_connected_get_collects_required_invoice_fields(self):
        response = self._submit_ticket(method="GET")
        self.assertEqual(response[0], "render")
        self.assertFalse(self.order.account_move)

    def test_extra_field_template_uses_model_defaults_and_associates_label(self):
        country = self.env.ref("base.us")
        field = self.env["ir.model.fields"]._get("res.partner", "country_id")
        markup = (
            self.env["ir.qweb"]
            .with_context(default_country_id=country.id)
            ._render(
                "account.portal_invoice_required_fields_form",
                {
                    "env": self.env,
                    "required_fields": field,
                    "field_prefix": "partner_",
                    "extra_field_values": {},
                },
            )
        )
        _logger.debug("Required country field HTML: %s", markup)
        document = html.fromstring(markup)
        self.assertEqual(
            document.xpath(
                "//select[@id='partner_country_id']/option[@selected]/@value"
            ),
            [str(country.id)],
        )
        self.assertEqual(document.xpath("//label/@for"), ["partner_country_id"])

    def test_extra_field_template_preserves_explicit_empty_value(self):
        field = self.env["ir.model.fields"]._get("account.move", "move_type")
        markup = self.env["ir.qweb"]._render(
            "account.portal_invoice_required_fields_form",
            {
                "env": self.env,
                "required_fields": field,
                "field_prefix": "invoice_",
                "extra_field_values": {"invoice_move_type": ""},
            },
        )
        document = html.fromstring(markup)
        self.assertEqual(document.xpath("//select/option[@selected]/@value"), [""])

    def test_extra_field_template_handles_invalid_relation_values(self):
        field = self.env["ir.model.fields"]._get("res.partner", "country_id")
        for value in ("²", "9" * 5000, "not-a-country"):
            with self.subTest(value=value[:20]):
                markup = self.env["ir.qweb"]._render(
                    "account.portal_invoice_required_fields_form",
                    {
                        "env": self.env,
                        "required_fields": field,
                        "field_prefix": "partner_",
                        "extra_field_values": {"partner_country_id": value},
                    },
                )
                document = html.fromstring(markup)
                self.assertGreater(len(document.xpath("//option")), 1)
                self.assertFalse(document.xpath("//option[@selected]"))

    def test_missing_extra_field_does_not_invoice_or_mutate_partner(self):
        response = self._submit_ticket(partner_function="Purchasing")
        self.assertEqual(response[0], "render")
        self.assertIn("invoice_source_email", response[2]["invalid_fields"])
        self.assertEqual(
            response[2]["extra_field_values"]["partner_function"], "Purchasing"
        )
        self.assertEqual(self.partner.function, "Buyer")
        self.assertFalse(self.order.account_move)

    def test_connected_post_accepts_extra_fields_without_address_inputs(self):
        response = self._submit_ticket(
            partner_function=self.partner.function,
            invoice_invoice_source_email="customer@example.test",
        )
        self.assertEqual(response[0], "redirect")
        self.assertEqual(self.order.account_move.state, "posted")
        self.assertEqual(
            self.order.account_move.invoice_source_email, "customer@example.test"
        )

    def test_invalid_address_retains_invoice_input(self):
        response = self._submit_ticket(
            partner_function=self.partner.function,
            invoice_invoice_source_email="customer@example.test",
            email="invalid",
        )
        self.assertEqual(response[0], "render")
        self.assertIn("email", response[2]["invalid_fields"])
        self.assertEqual(
            response[2]["extra_field_values"]["invoice_invoice_source_email"],
            "customer@example.test",
        )
        self.assertFalse(self.order.account_move)

    def test_same_named_fields_are_required_on_both_models(self):
        for values in (
            {"partner_ref": "Customer reference"},
            {"invoice_ref": "Invoice reference"},
        ):
            with self.subTest(values=values):
                response = self._submit_ticket(field_names=("ref", "ref"), **values)
                self.assertEqual(response[0], "render")
                self.assertIn("ref", response[2]["invalid_fields"])
                self.assertFalse(self.order.account_move)
                self.assertFalse(self.partner.ref)

    def test_locked_ticket_returns_retryable_conflict(self):
        with patch.object(
            type(self.env["res.company"]), "_with_locked_records", return_value=False
        ):
            response = self._submit_ticket()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.headers["Retry-After"], "1")
        self.assertIn("Please try again later", response.get_data(as_text=True))
        self.assertFalse(self.order.account_move)

    def test_submitted_keys_cannot_replace_validation_or_template_state(self):
        response = self._submit_ticket(
            partner_function="Purchasing",
            extra_field_values="untrusted",
            invalid_fields="untrusted",
            messages="untrusted",
            pos_order="untrusted",
            partner_sudo="untrusted",
            country="untrusted",
        )
        self.assertEqual(response[0], "render")
        self.assertEqual(response[2]["pos_order"], self.order)
        self.assertEqual(response[2]["partner_sudo"], self.partner)
        self.assertIn("invoice_source_email", response[2]["invalid_fields"])
        self.assertEqual(
            response[2]["extra_field_values"]["partner_function"], "Purchasing"
        )
        self.assertFalse(self.order.account_move)

    def test_whitespace_does_not_satisfy_required_invoice_field(self):
        response = self._submit_ticket(
            partner_function="Purchasing", invoice_invoice_source_email="   "
        )
        self.assertEqual(response[0], "render")
        self.assertIn("invoice_source_email", response[2]["invalid_fields"])
        self.assertEqual(self.partner.function, "Buyer")
        self.assertFalse(self.order.account_move)

    def test_invalid_selection_does_not_update_partner_or_invoice(self):
        response = self._submit_ticket(
            field_names=("function", "move_type"),
            partner_function="Purchasing",
            invoice_move_type="not-a-move-type",
        )
        self.assertEqual(response[0], "render")
        self.assertIn("move_type", response[2]["invalid_fields"])
        self.assertEqual(self.partner.function, "Buyer")
        self.assertFalse(self.order.account_move)

    def test_omitted_partner_field_preserves_its_display_default(self):
        response = self._submit_ticket(
            invoice_invoice_source_email="customer@example.test"
        )
        self.assertEqual(response[0], "render")
        self.assertIn("function", response[2]["invalid_fields"])
        self.assertEqual(response[2]["extra_field_values"]["partner_function"], "Buyer")
        self.assertFalse(self.order.account_move)

    def test_required_relation_rejects_invalid_or_missing_records(self):
        for record_id in ("0", "-1", "not-a-number", "2147483647"):
            with self.subTest(record_id=record_id):
                response = self._submit_ticket(
                    field_names=("country_id", "invoice_source_email"),
                    partner_country_id=record_id,
                    invoice_invoice_source_email="customer@example.test",
                )
                self.assertEqual(response[0], "render")
                self.assertIn("country_id", response[2]["invalid_fields"])
                self.assertEqual(self.partner.country_id, self.env.ref("base.us"))
                self.assertFalse(self.order.account_move)

    def test_valid_relation_and_selection_are_accepted(self):
        response = self._submit_ticket(
            field_names=("country_id", "auto_post"),
            partner_country_id=str(self.partner.country_id.id),
            invoice_auto_post="no",
        )
        self.assertEqual(response[0], "redirect")
        self.assertEqual(self.order.account_move.auto_post, "no")
        self.assertEqual(self.order.account_move.state, "posted")

    def test_invoice_defaults_do_not_change_payment_move_type(self):
        response = self._submit_ticket(
            field_names=("country_id", "move_type"),
            partner_country_id=str(self.partner.country_id.id),
            invoice_move_type="out_invoice",
        )
        self.assertEqual(response[0], "redirect")
        self.assertEqual(self.order.account_move.move_type, "out_invoice")
        payment_moves = self.order.payment_ids.account_move_id
        self.assertTrue(payment_moves)
        self.assertEqual(set(payment_moves.mapped("move_type")), {"entry"})
