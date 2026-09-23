from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    _parse_counter_names,
    pager,
)
from odoo.addons.portal.utils import (
    get_portal_partner,
    is_thread_hash_pid_valid,
    is_thread_token_valid,
    resolve_thread_for_credentials,
)


class PortalHardeningCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Hardening Customer", "email": "hardening@example.com"}
        )
        cls.portal_user = cls.env["res.users"].create(
            {
                "login": "portal_hardening",
                "password": "portal_hardening",
                "partner_id": cls.customer.id,
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )

    def _missing_thread(self, model="res.partner"):
        Model = self.env[model]
        highest = Model.sudo().search([], order="id desc", limit=1).id or 0
        return Model.sudo().browse(highest + 10_000_000)


class TestDeletedThreadCredentials(PortalHardeningCommon):
    def setUp(self):
        super().setUp()
        self.patch(
            self.env.registry["res.partner"], "_mail_post_token_field", "signup_type"
        )

    def test_reading_the_token_field_would_raise(self):
        from odoo.exceptions import MissingError

        with self.assertRaises(MissingError):
            self._missing_thread().signup_type

    def test_resolve_drops_a_phantom_record(self):
        self.assertFalse(resolve_thread_for_credentials(self._missing_thread()))

    def test_resolve_keeps_a_live_record(self):
        self.assertEqual(
            resolve_thread_for_credentials(self.customer.sudo()), self.customer.sudo()
        )

    def test_resolve_passes_an_empty_recordset_through(self):
        empty = self.env["res.partner"]
        self.assertEqual(resolve_thread_for_credentials(empty), empty)

    def test_get_portal_partner_on_deleted_record(self):
        self.assertFalse(
            get_portal_partner(
                self._missing_thread(), "a" * 64, self.customer.id, "a" * 32
            )
        )

    def test_get_thread_with_access_on_deleted_record(self):
        missing_id = self._missing_thread().id
        for creds in (
            {"token": "a" * 32},
            {"hash": "a" * 64, "pid": self.customer.id},
            {"hash": "a" * 64, "pid": self.customer.id, "token": "a" * 32},
        ):
            with self.subTest(creds=creds):
                self.assertFalse(
                    self.env["res.partner"]
                    .with_user(self.portal_user)
                    ._get_thread_with_access(missing_id, **creds)
                )

    def test_valid_credentials_still_grant_access(self):
        record = self.customer.sudo()
        record.signup_type = "a-live-token"
        self.assertTrue(is_thread_token_valid(record, "a-live-token"))
        self.assertTrue(
            is_thread_hash_pid_valid(
                record, record._sign_token(self.customer.id), self.customer.id
            )
        )
        self.assertEqual(
            get_portal_partner(record, None, None, "a-live-token"), self.customer
        )


class TestDocumentCheckAccess(PortalHardeningCommon):
    def test_token_against_model_without_token_field(self):
        cron = self.env["ir.cron"].sudo().search([], limit=1)
        self.assertNotIn("access_token", self.env["ir.cron"]._fields)

        controller = CustomerPortal()
        for access_token in ("some-token", None, 42, ["x"]):
            with self.subTest(access_token=access_token):
                with (
                    self.assertRaises(AccessError),
                    self._mock_request(),
                ):
                    controller._document_check_access(
                        "ir.cron", cron.id, access_token=access_token
                    )

    def _mock_request(self):
        from unittest.mock import patch

        from odoo.addons.portal.controllers import portal as portal_ctrl

        env_portal = self.env(user=self.portal_user)

        class Req:
            env = env_portal

        return patch.object(portal_ctrl, "request", Req())


class TestCounterNames(TransactionCase):
    def test_collections_keep_their_string_entries(self):
        self.assertEqual(
            _parse_counter_names(["a_count", "b_count"]), ["a_count", "b_count"]
        )
        self.assertEqual(_parse_counter_names(("a_count",)), ["a_count"])
        self.assertEqual(_parse_counter_names([]), [])

    def test_non_collections_request_nothing(self):
        for raw in (None, 42, 0, True, {"a_count": 1}, object()):
            with self.subTest(raw=raw):
                self.assertEqual(_parse_counter_names(raw), [])

    def test_bare_string_is_not_a_collection_of_names(self):
        self.assertEqual(_parse_counter_names("order_count"), [])

    def test_non_string_entries_are_dropped(self):
        self.assertEqual(
            _parse_counter_names(["a_count", 5, None, "b_count"]),
            ["a_count", "b_count"],
        )


class TestSearchbarOptionResolution(TransactionCase):
    def setUp(self):
        super().setUp()
        self.controller = CustomerPortal()
        self.options = {
            "date": {"label": "Newest", "order": "date desc"},
            "name": {"label": "Name", "order": "name"},
        }

    def test_known_key_is_kept(self):
        self.assertEqual(
            self.controller._resolve_searchbar_option(self.options, "name", "date"),
            "name",
        )

    def test_unknown_or_absent_key_falls_back(self):
        for key in ("bogus", "", None, 42, ["name"], {"name": 1}):
            with self.subTest(key=key):
                self.assertEqual(
                    self.controller._resolve_searchbar_option(
                        self.options, key, "date"
                    ),
                    "date",
                )

    def test_result_is_always_indexable_when_default_is_valid(self):
        for key in ("bogus", None, "name"):
            resolved = self.controller._resolve_searchbar_option(
                self.options, key, "date"
            )
            self.assertIn(resolved, self.options)

    def test_empty_vocabulary_returns_the_default_unchanged(self):
        self.assertEqual(
            self.controller._resolve_searchbar_option({}, "x", "date"), "date"
        )


class TestPagerEmptyResultSet(TransactionCase):
    def test_empty_total_has_no_page_zero(self):
        result = pager("/my/things", total=0)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(result["page"]["num"], 1)
        for key in ("page_first", "page_previous", "page_next", "page_last"):
            with self.subTest(key=key):
                self.assertEqual(result[key]["num"], 1, f"{key} must not be page 0")
                self.assertNotIn("/page/0", result[key]["url"])

    def test_empty_total_page_urls_have_no_page_suffix(self):
        result = pager("/my/things", total=0)
        self.assertEqual(result["page"]["url"], "/my/things")


class TestMailRenderSlugWithoutRequest(TransactionCase):
    def test_slug_is_not_request_bound_in_render_context(self):
        record = self.env["res.partner"].create({"name": "Slug Target"})
        slug = self.env["mail.template"]._render_eval_context()["slug"]
        self.assertEqual(slug(record), f"slug-target-{record.id}")

    def test_inline_template_field_renders_slug(self):
        record = self.env["res.partner"].create({"name": "Slug Subject"})
        template = self.env["mail.template"].create(
            {
                "name": "Slug probe",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "subject": "See {{ slug(object) }}",
            }
        )
        self.assertEqual(
            template._render_field("subject", record.ids)[record.id],
            f"See slug-subject-{record.id}",
        )

    def test_qweb_body_renders_slug(self):
        record = self.env["res.partner"].create({"name": "Slug Body"})
        template = self.env["mail.template"].create(
            {
                "name": "Slug body probe",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "body_html": '<p><a t-attf-href="/r/{{ slug(object) }}?n={{ 1 + 1 }}">go</a></p>',
            }
        )
        self.assertIn(
            f"/r/slug-body-{record.id}?n=2",
            template._render_field("body_html", record.ids)[record.id],
        )


@tagged("-at_install", "post_install")
class TestPortalRouteRobustness(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Route Customer", "email": "route@example.com"}
        )
        cls.portal_user = cls.env["res.users"].create(
            {
                "login": "portal_routes",
                "password": "portal_routes",
                "partner_id": cls.customer.id,
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )

    def setUp(self):
        super().setUp()
        self.patch(
            self.env.registry["res.partner"], "_mail_post_token_field", "signup_type"
        )

    def _missing_id(self, model="res.partner"):
        highest = self.env[model].sudo().search([], order="id desc", limit=1).id or 0
        return highest + 10_000_000

    @mute_logger("odoo.http")
    def test_chatter_init_on_deleted_record_is_not_an_error(self):
        missing = self._missing_id()
        for creds in (
            {"token": "a" * 32},
            {"hash": "a" * 64, "pid": self.customer.id},
        ):
            with self.subTest(creds=creds):
                body = self.url_open(
                    "/portal/chatter_init",
                    json={
                        "params": {
                            "thread_model": "res.partner",
                            "thread_id": missing,
                            **creds,
                        }
                    },
                ).json()
                self.assertNotIn("error", body, body.get("error"))

    @mute_logger("odoo.http")
    def test_chatter_fetch_on_deleted_record_is_a_plain_404(self):
        body = self.url_open(
            "/mail/chatter_fetch",
            json={
                "params": {
                    "thread_model": "res.partner",
                    "thread_id": self._missing_id(),
                    "token": "a" * 32,
                }
            },
        ).json()
        error = body.get("error", {})
        self.assertEqual(error.get("code"), 404)
        self.assertEqual(error["data"]["name"], "werkzeug.exceptions.NotFound")

    @mute_logger("odoo.http")
    def test_counters_rejects_non_collections_without_erroring(self):
        self.authenticate("portal_routes", "portal_routes")
        for counters in (42, None, "order_count", {"a": 1}, [None, 3]):
            with self.subTest(counters=counters):
                body = self.url_open(
                    "/my/counters", json={"params": {"counters": counters}}
                ).json()
                self.assertNotIn("error", body, body.get("error"))

    def test_counters_still_answers_a_valid_request(self):
        self.authenticate("portal_routes", "portal_routes")
        body = self.url_open(
            "/my/counters", json={"params": {"counters": ["unknown_count"]}}
        ).json()
        self.assertNotIn("error", body, body.get("error"))
        self.assertEqual(body["result"], {})
