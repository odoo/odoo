import logging
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from lxml import html

from odoo import Command
from odoo.http import Request
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    _get_url_with_params,
    _pager_url,
)

_logger = logging.getLogger(__name__)


class TestPortalPhoneIntegrity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Phone integrity",
                "phone_ids": [
                    Command.create({"number": "+32000111001", "primary": True}),
                    Command.create({"number": "+32000111002", "type": "emergency"}),
                ],
            }
        )

    def test_clearing_primary_preserves_secondary_and_shared_numbers(self):
        primary = self.partner._phone_get_number()
        secondary = self.partner.phone_ids - primary
        other = self.env["res.partner"].create(
            {
                "name": "Shared phone",
                "phone_ids": [Command.link(primary.id)],
            }
        )

        self.partner.write(
            CustomerPortal()._resolve_address_phone_values(
                {"phone": False}, self.partner
            )
        )

        _logger.debug(
            "Phone clear: remaining=%s shared=%s",
            self.partner.phone_ids.ids,
            other.phone_ids.ids,
        )
        self.assertEqual(self.partner.phone_ids, secondary)
        self.assertEqual(other.phone_ids, primary)

    def test_unchanged_phone_does_not_schedule_relational_writes(self):
        values = {"city": "Brussels", "phone": self.partner._phone_get_number().number}
        result = CustomerPortal()._resolve_address_phone_values(values, self.partner)

        _logger.debug("Unchanged phone: scheduled fields=%s", list(result))
        self.assertEqual(result, {"city": "Brussels"})
        self.assertIn("phone", values)

    def test_replacing_phone_does_not_modify_shared_number(self):
        primary = self.partner._phone_get_number()
        secondary = self.partner.phone_ids - primary
        other = self.env["res.partner"].create(
            {
                "name": "Shared replacement source",
                "phone_ids": [Command.link(primary.id)],
            }
        )
        self.partner.write(
            CustomerPortal()._resolve_address_phone_values(
                {"phone": "+32000111003"}, self.partner
            )
        )

        self.assertIn(secondary, self.partner.phone_ids)
        self.assertNotIn(primary, self.partner.phone_ids)
        self.assertEqual(primary.number, "+32000111001")
        self.assertEqual(other.phone_ids, primary)
        # The next page reads the relation in the phone model's persisted order.
        self.partner.invalidate_recordset(["phone_ids"])
        _logger.debug(
            "Phone replacement: primary=%s", self.partner._phone_get_number().id
        )
        self.assertEqual(self.partner._phone_get_number().number, "+32000111003")

    def test_replacement_remains_displayed_with_default_phone_priorities(self):
        self.partner.phone_ids.write({"primary": False, "sequence": 10})
        self.partner.invalidate_recordset(["phone_ids"])
        secondary = self.partner.phone_ids[1:]

        self.partner.write(
            CustomerPortal()._resolve_address_phone_values(
                {"phone": "+32000111004"}, self.partner
            )
        )
        self.partner.invalidate_recordset(["phone_ids"])

        _logger.debug(
            "Default-priority replacement: first=%s secondary=%s",
            self.partner._phone_get_number().id,
            secondary.ids,
        )
        self.assertIn(secondary, self.partner.phone_ids)
        self.assertEqual(self.partner._phone_get_number().number, "+32000111004")

    def test_shared_replacement_has_contact_owned_priority(self):
        target = self.env["phone.number"].create(
            {
                "number": "+32000111007",
                "sequence": 100,
                "type": "mobile",
            }
        )
        owner = self.env["res.partner"].create(
            {
                "name": "Other priority",
                "phone_ids": [
                    Command.create({"number": "+32000111008", "primary": True}),
                    Command.link(target.id),
                ],
            }
        )
        owner_primary = owner._phone_get_number()
        metadata = target.read(["primary", "sequence", "type", "number"])
        self.partner.write(
            CustomerPortal()._resolve_address_phone_values(
                {"phone": target.number},
                self.partner,
            )
        )
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Shared replacement: selected=%s legacy=%s owner=%s",
            self.partner._phone_get_number().id,
            self.partner.phone_ids._primary().id,
            owner._phone_get_number().id,
        )
        self.assertEqual(self.partner._phone_get_number(), target)
        # This is the original bug's counterexample: global ordering picks another number.
        self.assertNotEqual(self.partner.phone_ids._primary(), target)
        self.assertEqual(owner._phone_get_number(), owner_primary)
        self.assertEqual(
            target.read(["primary", "sequence", "type", "number"]), metadata
        )
        self.assertEqual(self.partner.main_mobile_id, target)
        with patch(
            "odoo.addons.portal.controllers.portal.request",
            SimpleNamespace(env=self.env),
        ):
            self.assertTrue(
                CustomerPortal()._are_same_addresses(
                    {"phone": target.number}, self.partner
                )
            )
        rendered = self.env["ir.qweb.field.contact"].value_to_html(
            self.partner,
            {"fields": ["phone"]},
        )
        self.assertIn(target.number, str(rendered))

    def test_new_address_resolves_shared_number_without_mutating_input(self):
        target = self.partner._phone_get_number()
        values = {"name": "New address", "phone": target.number}
        with patch(
            "odoo.addons.portal.controllers.portal.request",
            SimpleNamespace(env=self.env),
        ):
            resolved = CustomerPortal()._resolve_address_phone_values(values)
        partner = self.env["res.partner"].create(resolved)
        _logger.debug(
            "New address: selected=%s shared=%s",
            partner._phone_get_number().id,
            target.id,
        )
        self.assertEqual(partner._phone_get_number(), target)
        self.assertEqual(partner.preferred_phone_id, target)
        self.assertEqual(values, {"name": "New address", "phone": target.number})


class TestPortalPagerQuery(TransactionCase):
    def test_url_merge_replacement_append_and_empty_values(self):
        cases = [
            (
                {"token": "new"},
                True,
                [("tag", "a"), ("tag", "b"), ("blank", ""), ("token", "new")],
            ),
            (
                {"token": "new"},
                False,
                [
                    ("tag", "a"),
                    ("tag", "b"),
                    ("blank", ""),
                    ("token", "old"),
                    ("token", "new"),
                ],
            ),
            ({}, True, [("tag", "a"), ("tag", "b"), ("blank", ""), ("token", "old")]),
        ]
        for params, replace, expected in cases:
            with self.subTest(params=params, replace=replace):
                parsed = urlsplit(
                    _get_url_with_params(
                        "/my/document?tag=a&tag=b&blank=&token=old#details",
                        params,
                        replace,
                    )
                )
                self.assertEqual(parsed.path, "/my/document")
                self.assertEqual(parsed.fragment, "details")
                self.assertEqual(
                    parse_qsl(parsed.query, keep_blank_values=True), expected
                )

    def test_token_replaces_stale_value_without_losing_query_or_fragment(self):
        class Record:
            def __getitem__(self, key):
                return "/my/document/1?tag=a&tag=b&access_token=old#details"

            def _portal_get_or_create_token(self):
                return "new+token"

        parsed = urlsplit(_pager_url(Record(), "access_url"))
        self.assertEqual(parsed.fragment, "details")
        self.assertEqual(
            parse_qsl(parsed.query),
            [
                ("tag", "a"),
                ("tag", "b"),
                ("access_token", "new+token"),
            ],
        )

    def test_zipcode_alias_does_not_mutate_input_or_bypass_writable_fields(self):
        controller = CustomerPortal()
        data = {"zipcode": " 1000 "}
        with patch(
            "odoo.addons.portal.controllers.portal.request",
            SimpleNamespace(env=self.env),
        ):
            values, _extra = controller._parse_form_data(data)
            self.assertEqual(values["zip"], "1000")
            self.assertEqual(data, {"zipcode": " 1000 "})
            with patch.object(
                type(self.env["res.partner"]),
                "_get_fields_frontend_writable",
                return_value={"name"},
            ):
                values, _extra = controller._parse_form_data(data)
            self.assertNotIn("zip", values)


class TestPortalAddressRendering(TransactionCase):
    def test_account_keeps_details_breadcrumb(self):
        controller = CustomerPortal()
        with (
            patch(
                "odoo.addons.portal.controllers.portal.request",
                SimpleNamespace(env=self.env),
            ),
            patch.object(controller, "_prepare_address_form_values", return_value={}),
        ):
            values = controller._prepare_my_account_rendering_values()
        self.assertEqual(values["page_name"], "my_details")

    def test_country_format_without_city_renders_form_and_country_info(self):
        country = self.env.ref("base.be")
        country.address_format = "%(street)s\n%(zip)s\n%(country_name)s"
        partner = self.env.user.partner_id
        partner.country_id = country
        controller = CustomerPortal()
        with patch(
            "odoo.addons.portal.controllers.portal.request",
            SimpleNamespace(env=self.env),
        ):
            form = controller._prepare_address_form_values(partner)
            info = controller.portal_address_country_info(country, "billing")
        self.assertFalse(form["zip_before_city"])
        self.assertFalse(info["zip_before_city"])


@tagged("-at_install", "post_install")
class TestPortalAddressType(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = mail_new_test_user(
            cls.env,
            "portal_address_type",
            groups="base.group_portal",
        )
        cls.country = cls.env.ref("base.be")
        cls.portal_user.partner_id.write(
            {
                "country_id": cls.country.id,
                "street": "Challenge street",
                "city": "Brussels",
                "zip": "1000",
                "phone_ids": [Command.create({"number": "+32000111005"})],
            }
        )

    def _submit(self, **changes):
        partner = self.portal_user.partner_id
        values = {
            "partner_id": partner.id,
            "name": partner.name,
            "email": partner.email,
            "street": partner.street,
            "city": partner.city,
            "zip": partner.zip,
            "country_id": self.country.id,
            "phone": partner._phone_get_number().number,
            "csrf_token": Request.csrf_token(self),
            **changes,
        }
        response = self.url_open("/my/address/submit", data=values)
        _logger.debug(
            "Address challenge: fields=%s status=%s",
            sorted(changes),
            response.status_code,
        )
        return response

    def test_valid_types_save_and_missing_required_fields_do_not(self):
        self.authenticate("portal_address_type", "portal_address_type")
        for address_type in ("billing", "delivery"):
            with self.subTest(address_type=address_type):
                response = self._submit(address_type=address_type, city="New city")
                self.assertEqual(response.status_code, 200)
                self.assertIn("redirectUrl", response.json())
                self.portal_user.partner_id.invalidate_recordset()
                self.assertEqual(self.portal_user.partner_id.city, "New city")
                response = self._submit(
                    address_type=address_type, name="", city="Rejected city"
                )
                self.assertIn("name", response.json()["invalid_fields"])
                self.portal_user.partner_id.invalidate_recordset()
                self.assertEqual(self.portal_user.partner_id.city, "New city")

    def test_country_and_state_must_exist_and_agree(self):
        self.authenticate("portal_address_type", "portal_address_type")
        partner = self.portal_user.partner_id
        foreign_state = self.env.ref("base.state_us_1")
        unknown_country = (
            self.env["res.country"].search([], order="id desc", limit=1).id + 1
        )
        unknown_state = (
            self.env["res.country.state"].search([], order="id desc", limit=1).id + 1
        )
        for changes, field in (
            ({"country_id": unknown_country}, "country_id"),
            ({"state_id": unknown_state}, "state_id"),
            ({"state_id": foreign_state.id}, "state_id"),
        ):
            with self.subTest(changes=changes):
                response = self._submit(city="Must not save", **changes)
                _logger.debug(
                    "Geographic validation: %s status=%s body=%s",
                    changes,
                    response.status_code,
                    response.text[:500],
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.json()["invalid_fields"])
                partner.invalidate_recordset()
                self.assertEqual(partner.city, "Brussels")
                self.assertEqual(partner.country_id, self.country)
                self.assertFalse(partner.state_id)

    def test_country_change_cannot_retain_state_from_previous_country(self):
        partner = self.portal_user.partner_id
        state = self.env.ref("base.state_us_1")
        partner.write({"country_id": state.country_id.id, "state_id": state.id})
        self.authenticate("portal_address_type", "portal_address_type")
        response = self._submit(city="Must not save")
        _logger.debug("Country switch retaining state: %s", response.text[:500])
        self.assertIn("state_id", response.json()["invalid_fields"])
        partner.invalidate_recordset()
        self.assertEqual(partner.country_id, state.country_id)
        response = self._submit(state_id="")
        self.assertIn("redirectUrl", response.json())
        partner.invalidate_recordset()
        self.assertEqual(partner.country_id, self.country)
        self.assertFalse(partner.state_id)

    def test_new_address_requires_matching_state_and_accepts_valid_pair(self):
        self.authenticate("portal_address_type", "portal_address_type")
        partner = self.portal_user.partner_id
        state = self.env.ref("base.state_us_1")
        original_children = partner.child_ids
        response = self._submit(partner_id="", state_id=state.id)
        self.assertIn("state_id", response.json()["invalid_fields"])
        partner.invalidate_recordset()
        self.assertEqual(partner.child_ids, original_children)
        response = self._submit(
            partner_id="", state_id=state.id, country_id=state.country_id.id
        )
        self.assertIn("redirectUrl", response.json())
        partner.invalidate_recordset()
        created = partner.child_ids - original_children
        _logger.debug(
            "Valid address created: country=%s state=%s",
            created.country_id.id,
            created.state_id.id,
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(created.country_id, state.country_id)
        self.assertEqual(created.state_id, state)

    def test_postcode_alias_and_canonical_precedence_over_http(self):
        self.authenticate("portal_address_type", "portal_address_type")
        for zip_value, expected in (("", "2000"), ("3000", "3000")):
            with self.subTest(zip=zip_value):
                response = self._submit(zip=zip_value, zipcode=" 2000 ")
                self.assertIn("redirectUrl", response.json())
                self.portal_user.partner_id.invalidate_recordset()
                self.assertEqual(self.portal_user.partner_id.zip, expected)

    def test_default_portal_rejects_empty_phone_without_unlinking_numbers(self):
        partner = self.portal_user.partner_id
        partner.phone_ids = [
            Command.create({"number": "+32000111006", "type": "emergency"})
        ]
        original_numbers = partner.phone_ids
        self.authenticate("portal_address_type", "portal_address_type")

        response = self._submit(phone="")

        self.assertEqual(response.status_code, 200)
        self.assertIn("phone", response.json()["invalid_fields"])
        partner.invalidate_recordset(["phone_ids"])
        self.assertEqual(partner.phone_ids, original_numbers)

    def test_details_breadcrumb_and_postcode_only_country_over_http(self):
        self.country.address_format = "%(street)s\n%(zip)s\n%(country_name)s"
        self.authenticate("portal_address_type", "portal_address_type")
        response = self.url_open("/my/account")
        self.assertEqual(response.status_code, 200)
        document = html.fromstring(response.content)
        breadcrumbs = document.xpath("//ol[contains(@class, 'o_portal_submenu')]")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertIn("Details", breadcrumbs[0].text_content())
        self.assertEqual(len(document.xpath("//input[@name='zip']")), 1)
        info = self.call_jsonrpc(
            f"/my/address/country_info/{self.country.id}",
            params={"address_type": "billing"},
        )
        self.assertFalse(info["zip_before_city"])
        self.assertIn("zip", info["fields"])
        self.assertNotIn("city", info["fields"])

    def test_required_city_stays_editable_when_country_print_format_omits_it(self):
        self.country.address_format = "%(street)s\n%(zip)s\n%(country_name)s"
        self.portal_user.partner_id.city = False
        self.browser_js(
            "/my/account",
            """
            const city = document.querySelector('[name="city"]');
            console.debug("portal country challenge", {
                required: city.required, visible: city.getClientRects().length > 0,
            });
            if (!city.required || !city.getClientRects().length) {
                throw new Error("The server-required city must remain editable");
            }
            console.log("test successful");
            """,
            ready="document.querySelector('[name=phone]')?.placeholder === '+32'",
            login=self.portal_user.login,
        )

    def test_shared_phone_replacement_round_trip(self):
        partner = self.portal_user.partner_id
        partner.phone_ids = [Command.create({"number": "+32000111010", "sequence": 20})]
        target = self.env["phone.number"].create(
            {"number": "+32000111011", "sequence": 100}
        )
        other = self.env["res.partner"].create(
            {"name": "Shared destination", "phone_ids": [Command.link(target.id)]}
        )
        self.authenticate("portal_address_type", "portal_address_type")
        response = self._submit(phone=target.number)
        self.assertIn("redirectUrl", response.json())
        partner.invalidate_recordset()
        self.assertEqual(partner._phone_get_number(), target)
        self.assertEqual(other._phone_get_number(), target)
        document = html.fromstring(self.url_open("/my/account").content)
        displayed = document.xpath("//input[@name='phone']/@value")
        _logger.debug(
            "Phone HTTP round-trip: selected=%s displayed=%s", target.id, displayed
        )
        self.assertEqual(displayed, [target.number])

    def test_unknown_address_type_cannot_skip_required_fields(self):
        self.authenticate("portal_address_type", "portal_address_type")
        partner = self.portal_user.partner_id
        original_name = partner.name
        for address_type in ("other", "", "invoice"):
            with self.subTest(address_type=address_type):
                response = self.url_open(
                    "/my/address/submit",
                    data={
                        "partner_id": self.portal_user.partner_id.id,
                        "address_type": address_type,
                        "name": "",
                        "csrf_token": Request.csrf_token(self),
                    },
                )
                _logger.debug(
                    "Address type %r: HTTP %s", address_type, response.status_code
                )
                self.assertEqual(response.status_code, 400)
                partner.invalidate_recordset()
                self.assertEqual(partner.name, original_name)
