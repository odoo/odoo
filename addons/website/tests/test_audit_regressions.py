import re
from unittest.mock import MagicMock, patch

import psycopg
import requests
import werkzeug
from lxml import html

from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase, new_test_user
from odoo.tools import mute_logger

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website.controllers.main import Website


def _fake_google_response(content, content_type):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.headers = {"content-type": content_type}
    resp.iter_content.return_value = [content]
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


@tagged("post_install", "-at_install")
class TestWebsiteHostHeader(TransactionCase):
    def test_malformed_host_header_does_not_raise(self):
        website = self.env["website"].sudo()
        for host in (
            "a" * 64 + ".example.com",
            "a" * 300,
            "a..b",
            "",
            "example.com",
            "xn--e1afmkfd.xn--p1ai",
            "пример.рф",
        ):
            self.assertTrue(
                website._get_current_website_id(host),
                f"host {host!r} should resolve via fallback, not raise",
            )

    def test_domain_punycode_survives_malformed_domain(self):
        website = self.env["website"].create(
            {"name": "Punycode", "domain": "http://" + "a" * 64 + ".example.com"}
        )
        self.assertTrue(website.domain_punycode)

    def test_domain_punycode_only_rewrites_the_host(self):
        website = self.env["website"].create(
            {"name": "Echo", "domain": "http://ex.com/go?to=ex.com"}
        )
        self.assertEqual(website.domain_punycode, "http://ex.com/go?to=ex.com")


@tagged("post_install", "-at_install")
class TestTemplateCacheInvalidation(TransactionCase):
    def test_blocklist_change_takes_effect(self):
        website = self.env["website"].browse(1)
        website.write(
            {
                "cookies_bar": True,
                "block_third_party_domains": True,
                "custom_blocked_third_party_domains": "unrelated.test",
            }
        )
        self.env["ir.ui.view"].create(
            {
                "name": "audit_blocklist",
                "type": "qweb",
                "key": "website.audit_blocklist",
                "arch_db": (
                    '<t t-name="website.audit_blocklist"><div>'
                    '<iframe src="https://tracker.audit.test/pixel"/>'
                    "</div></t>"
                ),
            }
        )
        self.env.flush_all()

        public_env = self.env(
            user=self.env.ref("base.public_user"),
            context={"website_id": website.id, "lang": "en_US"},
        )

        def render():
            with MockRequest(public_env, website=website):
                return str(public_env["ir.qweb"]._render("website.audit_blocklist"))

        self.assertNotIn(
            "about:blank", render(), "not blocked yet: domain is not on the list"
        )

        website.write(
            {"custom_blocked_third_party_domains": "unrelated.test\ntracker.audit.test"}
        )
        self.env.flush_all()

        self.assertIn(
            "about:blank",
            render(),
            "adding a domain to the blocklist must take effect immediately",
        )


@tagged("post_install", "-at_install")
class TestMenuUnlinkFanout(TransactionCase):
    def test_generic_container_unlink_spares_other_websites(self):
        Menu = self.env["website.menu"]
        main_menu = self.env.ref("website.main_menu")
        website_2 = self.env["website"].create({"name": "Audit W2"})

        victim = Menu.create(
            {
                "name": "Victim",
                "parent_id": website_2.menu_id.id,
                "website_id": website_2.id,
            }
        )
        victim_child = Menu.create(
            {
                "name": "VictimChild",
                "parent_id": victim.id,
                "url": "/victim-child",
                "website_id": website_2.id,
            }
        )
        generic = Menu.create({"name": "GenericDrop", "parent_id": main_menu.id})
        Menu.create({"name": "GenericChild", "parent_id": generic.id, "url": "/gc"})
        Menu.invalidate_model()
        self.assertEqual(victim.url, "#", "a menu with children is a '#' container")
        self.assertEqual(generic.url, "#", "so is the generic one")

        generic.unlink()
        Menu.invalidate_model()

        self.assertTrue(victim.exists(), "website 2's unrelated dropdown must survive")
        self.assertTrue(victim_child.exists(), "and so must its child")

    def test_generic_navigable_unlink_still_removes_copies(self):
        Menu = self.env["website.menu"]
        main_menu = self.env.ref("website.main_menu")
        self.env["website"].create({"name": "Audit W2"})

        generic = Menu.create(
            {"name": "Shop", "url": "/audit-shop", "parent_id": main_menu.id}
        )
        Menu.invalidate_model()
        copies = Menu.search([("url", "=", "/audit-shop"), ("website_id", "!=", False)])
        self.assertTrue(copies, "create() should have made per-website copies")

        generic.unlink()
        Menu.invalidate_model()
        self.assertFalse(
            copies.exists(), "per-website copies of a navigable menu must be removed"
        )


@tagged("post_install", "-at_install")
class TestMultiWebsitePageScoping(TransactionCase):
    def test_is_homepage_is_website_scoped(self):
        website_1 = self.env["website"].browse(1)
        website_2 = self.env["website"].create({"name": "Audit W2"})
        page = self.env["website.page"].search(
            [("website_id", "in", (False, website_1.id))], limit=1
        )
        self.assertTrue(page, "need at least one page")
        website_1.homepage_url = page.url
        website_2.homepage_url = "/audit-not-this-page"
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertTrue(page.with_context(website_id=website_1.id).is_homepage)
        self.assertFalse(
            page.with_context(website_id=website_2.id).is_homepage,
            "website 1's answer must not leak into website 2's context",
        )

        self.env.invalidate_all()
        self.assertFalse(page.with_context(website_id=website_2.id).is_homepage)
        self.assertTrue(page.with_context(website_id=website_1.id).is_homepage)

    def test_page_rename_does_not_repoint_other_websites(self):
        website_1 = self.env["website"].browse(1)
        website_2 = self.env["website"].create({"name": "Audit W2"})

        def make_page(key, website):
            view = self.env["ir.ui.view"].create(
                {
                    "name": key,
                    "type": "qweb",
                    "key": f"website.{key}",
                    "arch_db": f'<t t-name="website.{key}"><div>{key}</div></t>',
                }
            )
            return self.env["website.page"].create(
                {"view_id": view.id, "url": "/audit-about", "website_id": website.id}
            )

        page_1 = make_page("audit_about_1", website_1)
        make_page("audit_about_2", website_2)
        website_1.homepage_url = "/audit-about"
        website_2.homepage_url = "/audit-about"
        self.env.flush_all()

        page_1.write({"url": "/audit-about-us"})
        self.env.flush_all()

        self.assertEqual(
            website_1.homepage_url, "/audit-about-us", "w1 follows its page"
        )
        self.assertEqual(
            website_2.homepage_url,
            "/audit-about",
            "w2 keeps pointing at its own page, which was not renamed",
        )


@tagged("post_install", "-at_install")
class TestWebsiteFormIntegrityError(TransactionCase):
    def test_constraint_violation_returns_false_not_500(self):
        self.env.ref("base.model_res_partner").website_form_access = True
        self.env["ir.model.fields"].formbuilder_whitelist("res.partner", ["name"])
        controller = WebsiteForm()
        original_insert_record = controller.create_record

        def failing_insert_record(*args, **kwargs):
            original_insert_record(*args, **kwargs)
            self.env.cr.execute(
                "INSERT INTO res_company_users_rel (cid, user_id) VALUES (%s, %s)",
                (2147483000, 2147483001),
            )

        controller.create_record = failing_insert_record
        with MockRequest(self.env):
            request.params = {"model_name": "res.partner", "name": "audit partner"}
            response = controller.website_form(**request.params)
            self.assertEqual(response.status_code, 200, "must not be a 500")
            self.assertEqual(
                response.data,
                b"false",
                "a constraint violation must return the graceful 'false'",
            )
            self.env.cr.execute("SELECT 1")
            self.assertEqual(self.env.cr.fetchone()[0], 1)


@tagged("post_install", "-at_install")
class TestVisitorPageSearch(TransactionCase):
    def test_search_by_page_id_finds_visitor(self):
        page = self.env["website.page"].search([], limit=1)
        self.assertTrue(page, "need at least one page")
        visitor = self.env["website.visitor"].create({"access_token": "a" * 32})
        # a visit is a track with a url; page_ids is computed over those, and
        # its search reads the same tracks
        self.env["website.track"].create(
            {"visitor_id": visitor.id, "page_id": page.id, "url": page.url}
        )
        self.env.flush_all()

        self.assertEqual(visitor.page_ids, page)
        self.assertIn(
            visitor,
            self.env["website.visitor"].search([("page_ids", "in", [page.id])]),
            "searching visitors by visited page id must find the visitor",
        )


@tagged("post_install", "-at_install")
class TestCustomAssetIsolation(TransactionCase):
    def test_custom_scss_does_not_bleed_across_websites(self):
        Assets = self.env["website.assets"]
        website_1 = self.env["website"].browse(1)
        website_2 = self.env["website"].create({"name": "Audit W2"})
        target = "/website/static/src/scss/options/user_values.scss"
        bundle = "web.assets_frontend"

        Assets.with_context(website_id=website_1.id).save_asset(
            target, bundle, "a.audit-probe{color:#ff0000}", "scss"
        )
        Assets.with_context(website_id=website_2.id).save_asset(
            target, bundle, "a.audit-probe{color:#0000ff}", "scss"
        )
        self.env.flush_all()

        compiled = {}
        for website in (website_1, website_2):
            asset_bundle = (
                self.env["ir.qweb"]
                .with_context(website_id=website.id)
                ._get_asset_bundle(bundle, css=True, js=False)
            )
            asset_bundle.css()
            compiled[website.id] = asset_bundle
        self.env.flush_all()

        for website, expected in ((website_1, b"red"), (website_2, b"blue")):
            url_prefix = f"/web/assets/{website.id}/"
            attachment = (
                self.env["ir.attachment"]
                .sudo()
                .search(
                    [
                        ("url", "=like", f"{url_prefix}%{bundle}%.css"),
                    ],
                    limit=1,
                )
            )
            self.assertTrue(attachment, f"website {website.id} should have a bundle")
            self.assertIn(
                b".audit-probe{color:" + expected,
                attachment.raw,
                f"website {website.id} must be served its OWN customisation",
            )


@tagged("post_install", "-at_install")
class TestControllerPageSlugPerWebsite(TransactionCase):
    def _make_page(self, website, view_key):
        view = self.env["ir.ui.view"].create(
            {
                "name": view_key,
                "type": "qweb",
                "key": f"website.{view_key}",
                "arch": '<t t-name="x"><div>x</div></t>',
                "website_id": website.id,
            }
        )
        return self.env["website.controller.page"].create(
            {
                "name": "AuditProducts",
                "view_id": view.id,
                "model_id": self.env["ir.model"]._get_id("res.partner"),
            }
        )

    def test_same_slug_allowed_on_two_websites(self):
        website_1 = self.env["website"].browse(1)
        website_2 = self.env["website"].create({"name": "Audit Slug W2"})
        self._make_page(website_1, "audit_slug_a")
        self._make_page(website_2, "audit_slug_b")
        self.env.flush_all()

    def test_same_slug_rejected_on_same_website(self):
        website_1 = self.env["website"].browse(1)
        self._make_page(website_1, "audit_slug_c")
        self.env.flush_all()
        with self.assertRaises(psycopg.errors.UniqueViolation), mute_logger("odoo.db"):
            self._make_page(website_1, "audit_slug_d")
            self.env.flush_all()


@tagged("post_install", "-at_install")
class TestWebsiteFormTagsUnescape(TransactionCase):
    def test_tags_unescape(self):
        tags = WebsiteForm().tags
        self.assertEqual(tags("t", "a,b,c"), ["a", "b", "c"])
        self.assertEqual(tags("t", r"a\,b,c"), ["a,b", "c"])
        self.assertEqual(tags("t", r"a\\b"), [r"a\b"])


@tagged("post_install", "-at_install")
class TestResetTemplateAuthz(TransactionCase):
    def test_portal_user_forbidden(self):
        portal = new_test_user(
            self.env, login="audit_portal", groups="base.group_portal"
        )
        view = self.env["ir.ui.view"].search([("type", "=", "qweb")], limit=1)
        controller = Website()
        with MockRequest(self.env(user=portal)):
            with self.assertRaises(werkzeug.exceptions.Forbidden):
                controller.reset_template(view_id=view.id)


@tagged("post_install", "-at_install")
class TestPlausibleShareUrlParsing(TransactionCase):
    def test_share_url_is_split_into_key_and_site(self):
        config = self.env["res.config.settings"].create(
            {"website_id": self.env["website"].browse(1).id}
        )
        config.plausible_shared_key = (
            "https://plausible.io/share/example.com?auth=SECRET123&period=30d"
        )
        config._onchange_shared_key()
        self.assertEqual(config.plausible_shared_key, "SECRET123")
        self.assertEqual(config.plausible_site, "example.com")


@tagged("post_install", "-at_install")
class TestGoogleFontFetchHardening(TransactionCase):
    _CSS = (
        b"@font-face{font-family:'Test';"
        b"src: url(https://fonts.gstatic.com/s/test/v1/abc.woff2) format('woff2');}"
    )

    def _localize(self, css_response, bin_response):
        def fake_request(session, method, url, **kw):
            return css_response() if "fonts.googleapis.com" in url else bin_response()

        with patch.object(GuardedSession, "request", fake_request):
            return self.env["website.assets"]._localize_google_fonts({"Test": ""})

    def _binary_count(self):
        return self.env["ir.attachment"].search_count(
            [("name", "=like", "google-font-%")]
        )

    def test_happy_path_localises_and_rewrites(self):
        resolved = self._localize(
            lambda: _fake_google_response(self._CSS, "text/css"),
            lambda: _fake_google_response(b"woff2-bytes", "font/woff2"),
        )
        self.assertTrue(resolved.get("Test"), "font should be localised")
        css = self.env["ir.attachment"].browse(resolved["Test"])
        self.assertIn(b"/web/content/", css.raw, "src rewritten to a local url")

    def test_network_failure_drops_font_without_raising(self):
        def boom():
            raise requests.ConnectionError("boom")

        resolved = self._localize(
            boom, lambda: _fake_google_response(b"x", "font/woff2")
        )
        self.assertNotIn("Test", resolved, "an unfetchable font is dropped, not a 500")

    def test_oversized_binary_is_not_stored(self):
        before = self._binary_count()
        oversized = b"x" * (5 * 1024 * 1024 + 1)
        resolved = self._localize(
            lambda: _fake_google_response(self._CSS, "text/css"),
            lambda: _fake_google_response(oversized, "font/woff2"),
        )
        css = self.env["ir.attachment"].browse(resolved["Test"])
        self.assertIn(b"fonts.gstatic.com", css.raw, "remote src kept on reject")
        self.assertEqual(before, self._binary_count(), "oversized bytes not stored")

    def test_non_font_content_type_is_rejected(self):
        before = self._binary_count()
        resolved = self._localize(
            lambda: _fake_google_response(self._CSS, "text/css"),
            lambda: _fake_google_response(b"<html>nope", "text/html"),
        )
        css = self.env["ir.attachment"].browse(resolved["Test"])
        self.assertIn(b"fonts.gstatic.com", css.raw)
        self.assertEqual(before, self._binary_count(), "non-font payload rejected")


@tagged("post_install", "-at_install")
class TestVisitorUpsertSeam(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Visitor = self.env["website.visitor"]
        self.website = self.env["website"].browse(1)
        self.lang = self.env["res.lang"].search([("active", "=", True)], limit=1)

    def test_upsert_creates_visitor_with_explicit_values(self):
        vid, inserted = self.Visitor._upsert_visitor(
            "a" * 32,
            lang_id=self.lang.id,
            country_code="US",
            website_id=self.website.id,
            timezone="Europe/Brussels",
        )
        self.assertTrue(inserted, "a fresh token must INSERT")
        self.env.invalidate_all()
        visitor = self.Visitor.browse(vid)
        self.assertEqual(visitor.access_token, "a" * 32)
        self.assertEqual(visitor.lang_id, self.lang)
        self.assertEqual(visitor.website_id, self.website)
        self.assertEqual(visitor.timezone, "Europe/Brussels")
        self.assertEqual(visitor.country_id.code, "US")
        self.assertFalse(visitor.partner_id, "a 32-char token is anonymous")

    def test_upsert_backfills_timezone_on_conflict(self):
        token = "b" * 32
        vid, _ = self.Visitor._upsert_visitor(
            token,
            lang_id=self.lang.id,
            country_code="",
            website_id=self.website.id,
            timezone="",
        )
        self.env.invalidate_all()
        self.assertFalse(self.Visitor.browse(vid).timezone)
        vid2, inserted = self.Visitor._upsert_visitor(
            token,
            lang_id=self.lang.id,
            country_code="",
            website_id=self.website.id,
            timezone="Asia/Tokyo",
        )
        self.assertFalse(inserted, "the same token must UPDATE, not insert")
        self.assertEqual(vid2, vid)
        self.env.invalidate_all()
        self.assertEqual(
            self.Visitor.browse(vid).timezone,
            "Asia/Tokyo",
            "a tz that arrives on a later visit must be back-filled",
        )

    def test_upsert_visit_count_respects_the_8h_window(self):
        token = "c" * 32
        kw = {
            "lang_id": self.lang.id,
            "country_code": "",
            "website_id": self.website.id,
            "timezone": "",
        }
        vid, _ = self.Visitor._upsert_visitor(token, **kw)
        self.env.invalidate_all()
        self.assertEqual(self.Visitor.browse(vid).visit_count, 1)
        self.Visitor._upsert_visitor(token, **kw)
        self.env.invalidate_all()
        self.assertEqual(self.Visitor.browse(vid).visit_count, 1)
        self.env.cr.execute(
            "UPDATE website_visitor "
            "SET last_connection_datetime = (now() at time zone 'UTC') - INTERVAL '9 hours' "
            "WHERE id = %s",
            (vid,),
        )
        self.env.invalidate_all()
        self.Visitor._upsert_visitor(token, **kw)
        self.env.invalidate_all()
        self.assertEqual(self.Visitor.browse(vid).visit_count, 2)

    def test_upsert_partner_token_links_partner(self):
        partner = self.env["res.partner"].create({"name": "Audit Visitor"})
        vid, _ = self.Visitor._upsert_visitor(
            partner.id,
            lang_id=self.lang.id,
            country_code="",
            website_id=self.website.id,
            timezone="",
        )
        self.env.invalidate_all()
        self.assertEqual(
            self.Visitor.browse(vid).partner_id,
            partner,
            "a non-32-char (partner id) token links the partner",
        )


@tagged("post_install", "-at_install")
class TestProtectedPageUnlock(HttpCase):
    URL = "/test-audit-protected"
    BODY = "AUDITSECRETBODY"

    def setUp(self):
        super().setUp()
        page = self.env["website.page"].create(
            {
                "name": "Audit Secret",
                "url": self.URL,
                "is_published": True,
                "type": "qweb",
                "key": "website.test_audit_protected",
                "arch": '<t t-name="website.test_audit_protected">'
                '<t t-call="website.layout">%s</t></t>' % self.BODY,
            }
        )
        page.view_id.write({"visibility": "password", "visibility_password": "hunter2"})
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.addCleanup(self.env.registry.clear_cache)
        self.addCleanup(page.unlink)

    def _get(self, **params):
        return self.url_open(self.URL, params=params, allow_redirects=False)

    def test_unlock_survives_the_next_request(self):
        denied = self._get()
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(self.BODY, denied.text)

        opened = self._get(visibility_password="hunter2")
        self.assertEqual(opened.status_code, 200)
        self.assertIn(self.BODY, opened.text)

        again = self._get()
        self.assertEqual(
            again.status_code,
            200,
            "the unlock must be remembered for the rest of the session",
        )
        self.assertIn(self.BODY, again.text)

    def test_a_protected_page_is_marked_uncacheable(self):
        self.assertEqual(self._get(visibility_password="hunter2").status_code, 200)
        opened = self._get()
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(
            opened.headers.get("Cache-Control"), "private, no-store, max-age=0"
        )
        plain = self.url_open("/", allow_redirects=False)
        self.assertEqual(plain.status_code, 200)
        self.assertIsNone(plain.headers.get("Cache-Control"))

    def test_a_wrong_password_never_unlocks(self):
        self.assertEqual(self._get(visibility_password="nope").status_code, 403)
        self.assertEqual(self._get().status_code, 403)

    def test_the_unlock_does_not_leak_through_the_page_cache(self):
        self.assertEqual(self._get(visibility_password="hunter2").status_code, 200)
        self.assertEqual(self._get().status_code, 200)

        self.opener.cookies.pop("session_id", None)
        denied = self._get()
        self.assertEqual(
            denied.status_code, 403, "a protected page must not be served from cache"
        )
        self.assertNotIn(self.BODY, denied.text)


@tagged("post_install", "-at_install")
class TestFrontendDispatchGeoip(HttpCase):
    def test_frontend_survives_a_geoip_that_knows_no_timezone(self):
        website = self.env["website"].search([], limit=1)
        website.user_id.sudo().tz = False
        self.env.flush_all()
        self.env.registry.clear_cache()

        response = self.url_open("/", allow_redirects=False)
        self.assertEqual(
            response.status_code,
            200,
            "an anonymous frontend request must not depend on a GeoIP city database",
        )


@tagged("post_install", "-at_install")
class TestCookiesBarCookie(HttpCase):
    def setUp(self):
        super().setUp()
        self.website = self.env["website"].search([], limit=1)
        self.website.write({"cookies_bar": True})
        self.website.user_id.sudo().tz = False
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.addCleanup(self.env.registry.clear_cache)
        self.addCleanup(self.website.write, {"cookies_bar": False})

    def test_a_malformed_consent_cookie_does_not_take_the_site_down(self):
        for value in ("garbage", '{"optional":', "[1,2"):
            response = self.url_open(
                "/",
                cookies={"website_cookies_bar": value},
                allow_redirects=False,
            )
            self.assertEqual(
                response.status_code,
                200,
                f"a malformed consent cookie ({value!r}) must not 500 the page",
            )


@tagged("post_install", "-at_install")
class TestGetCurrentWebsiteCost(TransactionCase):
    def test_a_forced_website_is_not_re_checked_on_every_call(self):
        website = self.env["website"].search([], limit=1)
        Website = self.env["website"]
        with MockRequest(self.env, website=website) as req:
            req.session["force_website_id"] = website.id
            self.env.registry.clear_cache()
            Website.get_current_website()
            with self.assertQueryCount(0):
                for _i in range(20):
                    self.assertEqual(Website.get_current_website(), website)

    def test_a_deleted_forced_website_is_still_dropped_from_the_session(self):
        website = self.env["website"].search([], limit=1)
        missing_id = max(self.env["website"].search([]).ids) + 1000
        with MockRequest(self.env, website=website) as req:
            req.session["force_website_id"] = missing_id
            self.env.registry.clear_cache()
            self.assertTrue(self.env["website"].get_current_website())
            self.assertNotIn(
                "force_website_id",
                req.session,
                "a forced website that no longer exists must be dropped",
            )


@tagged("post_install", "-at_install")
class TestSnippetAssetPruning(TransactionCase):
    def test_a_snippet_template_without_a_class_does_not_break_the_upgrade(self):
        self.env["ir.ui.view"].create(
            {
                "name": "Audit classless snippet",
                "type": "qweb",
                "key": "website.audit_classless_snippet",
                "arch": '<div t-name="website.audit_classless_snippet">x</div>',
            }
        )
        self.env.registry.clear_cache()
        used = self.env["website"]._is_snippet_used(
            "website",
            "audit_classless_snippet",
            "000",
            "js",
            [("ir.ui.view", "arch_db")],
        )
        self.assertIn(used, (True, False))


@tagged("post_install", "-at_install")
class TestCookieBarrierWithoutRequest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.website = self.env["website"].browse(1)
        self.website.write({"cookies_bar": True, "block_third_party_domains": True})
        self.env["ir.ui.view"].create(
            {
                "name": "audit_norequest",
                "type": "qweb",
                "key": "website.audit_norequest",
                "arch_db": '<t t-name="website.audit_norequest"><div>'
                '<iframe src="https://www.youtube.com/embed/x"/></div></t>',
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.addCleanup(self.env.registry.clear_cache)

    def _render_without_request(self):
        return str(
            self.env["ir.qweb"]
            .with_context(website_id=self.website.id)
            ._render("website.audit_norequest")
        )

    def test_a_request_free_render_does_not_raise(self):
        self.assertIn("<iframe", self._render_without_request())

    def test_a_request_free_render_still_blocks_third_parties(self):
        rendered = self._render_without_request()
        iframe = html.fromstring(rendered).xpath("//iframe")[0]
        self.assertEqual(iframe.get("src"), "about:blank")
        self.assertEqual(
            iframe.get("data-nocookie-src"), "https://www.youtube.com/embed/x"
        )
        self.assertEqual(iframe.get("data-need-cookies-approval"), "true")


@tagged("post_install", "-at_install")
class TestSecondAuditRegressions(TransactionCase):
    def test_public_snippet_filter_rejects_an_unknown_model(self):
        empty_filter = self.env["website.snippet.filter"]
        self.assertEqual(
            empty_filter._render(
                template_key="website.dynamic_filter_template_x",
                limit=1,
                search_domain=[],
                with_sample=True,
                res_model="bogus.model",
                res_id=1,
            ),
            [],
        )

    def test_new_page_rejects_a_template_that_is_not_module_dot_name(self):
        for bad in ("nodot", "a.b.c"):
            with self.subTest(template=bad), self.assertRaises(UserError):
                self.env["website"].new_page(name="probe", template=bad)

    def test_page_creation_does_not_rebind_another_website_s_menu(self):
        website_a = self.env["website"].search([], limit=1)
        website_b = self.env["website"].create({"name": "Audit site B"})
        foreign_menu = self.env["website.menu"].create(
            {
                "name": "Foreign",
                "url": "/audit-collide",
                "website_id": website_b.id,
                "parent_id": website_b.menu_id.id,
            }
        )

        controller = Website()
        with MockRequest(self.env, website=website_a):
            controller.pagenew(path="audit-collide")

        page = self.env["website.page"].search(
            [("url", "=", "/audit-collide"), ("website_id", "=", website_a.id)]
        )
        self.assertTrue(page, "the page was not created on the current website")
        foreign_menu.invalidate_recordset()
        self.assertFalse(
            foreign_menu.page_id,
            "a menu of another website was repointed at this website's page",
        )

    def test_created_website_gets_a_public_user_of_its_own_company(self):
        other_company = self.env["res.company"].create({"name": "Audit Co"})
        website = (
            self.env["website"]
            .with_company(other_company)
            .create({"name": "Audit company site"})
        )
        self.assertEqual(website.company_id, other_company)
        self.assertEqual(website.sudo().user_id.company_id, other_company)

    def test_visitor_page_count_ignores_untracked_urls(self):
        website = self.env["website"].search([], limit=1)
        visitor = self.env["website.visitor"].create(
            {"access_token": "a" * 32, "website_id": website.id}
        )
        self.env["website.track"].create(
            [
                {"visitor_id": visitor.id, "url": "/untracked-a"},
                {"visitor_id": visitor.id, "url": "/untracked-b"},
            ]
        )
        visitor.invalidate_recordset()
        self.assertEqual(visitor.page_count, 0)
        self.assertEqual(visitor.sudo().page_ids.ids, [])
        self.assertEqual(visitor.visitor_page_count, 2)

    def test_blocked_third_party_domains_reach_the_client_normalised(self):
        website = self.env["website"].search([], limit=1)
        website.sudo().custom_blocked_third_party_domains = (
            "#ignore_default\n  Tracker.Example.COM  \nsecond.test\n"
        )
        self.assertEqual(
            website._get_blocked_third_party_domains_list(),
            ["tracker.example.com", "second.test"],
        )

    def test_website_restriction_does_not_mutate_the_shared_converter(self):
        from odoo.addons.website.models.ir_http import ModelConverter

        converter = ModelConverter.__new__(ModelConverter)
        converter.model = "website.page"
        converter.domain = "[]"

        list(
            converter.generate(
                self.env,
                args={},
                domain="[('website_id', 'in', (False, current_website_id))]",
            )
        )

        self.assertEqual(
            converter.domain,
            "[]",
            "the registry-cached routing map's converter was mutated",
        )

    def test_password_visibility_without_a_password_denies_instead_of_500(self):
        view = self.env["ir.ui.view"].search([("type", "=", "qweb")], limit=1)
        protected = view.copy({"key": "website.audit_pwd_probe"})
        protected.sudo().write({"visibility": "password"})
        self.assertFalse(protected.sudo().visibility_password)

        website = self.env["website"].search([], limit=1)
        public_user = self.env.ref("base.public_user")
        with MockRequest(self.env(user=public_user), website=website) as req:
            req.params = {"visibility_password": "any guess"}
            with self.assertRaises(werkzeug.exceptions.Forbidden):
                protected._handle_visibility()


@tagged("post_install", "-at_install")
class TestPageLookupIsLiteral(HttpCase):
    def test_underscore_and_percent_in_a_missing_url_are_not_wildcards(self):
        website = self.env["website"].get_current_website()
        self.env["website"].new_page(
            "abc-literal", page_values={"is_published": True, "url": "/abc-literal"}
        )
        self.env["website.page"].search([("url", "=", "/abc-literal")]).write(
            {"website_id": website.id}
        )
        for missing in ("/a_c-literal", "/%25bc-literal"):
            res = self.url_open(missing, allow_redirects=False)
            self.assertEqual(
                res.status_code,
                404,
                (missing, res.status_code, res.headers.get("Location")),
            )


@tagged("post_install", "-at_install")
class TestAltAndLinkUpdatesEscapeOnce(TransactionCase):
    def test_alt_and_href_are_escaped_by_the_serializer_only(self):
        website = self.env["website"].get_current_website()
        view = self.env["ir.ui.view"].create(
            {
                "name": "escape once",
                "type": "qweb",
                "key": "website.test_escape_once",
                "arch": '<div><img src="/x"/><a href="/old">l</a></div>',
            }
        )
        with MockRequest(self.env, website=website):
            Website().update_alt_images(
                [
                    {
                        "res_model": "ir.ui.view",
                        "res_id": view.id,
                        "field": "arch",
                        "id": f"ir.ui.view-{view.id}-0",
                        "decorative": False,
                        "alt": 'Tom & "Jerry"',
                    }
                ]
            )
            Website().update_broken_links(
                [
                    {
                        "res_model": "ir.ui.view",
                        "res_id": view.id,
                        "field": "arch",
                        "oldLink": "/old",
                        "newLink": "/x?a=1&b=2",
                        "remove": False,
                    }
                ]
            )
        arch = view.arch
        self.assertNotIn("&amp;amp;", arch, arch)
        self.assertIn('alt="Tom &amp; &quot;Jerry&quot;"', arch, arch)
        self.assertIn('href="/x?a=1&amp;b=2"', arch, arch)


@tagged("post_install", "-at_install")
class TestCdnFiltersAreValidated(TransactionCase):
    def test_an_invalid_regex_is_refused_at_write_time(self):
        website = self.env["website"].get_current_website()
        with self.assertRaises(ValidationError):
            website.write({"cdn_filters": "^/web/(\n^/ok/"})
        website.write({"cdn_activated": True, "cdn_url": "https://cdn.example.com"})
        website.write({"cdn_filters": "^/web/\n\n^/ok/"})
        self.assertEqual(
            website.get_cdn_url("/web/assets/x.js"),
            "https://cdn.example.com/web/assets/x.js",
        )


@tagged("post_install", "-at_install")
class TestPageWriteKeepsAnExplicitKey(TransactionCase):
    def test_key_written_beside_name_is_kept(self):
        result = self.env["website"].new_page(
            "keyed", page_values={"is_published": True}
        )
        page = self.env["website.page"].browse(result["page_id"])
        page.write({"name": "Renamed", "key": "website.explicit_key"})
        self.assertEqual(page.key, "website.explicit_key")
        self.assertEqual(page.name, "Renamed")
        page.write({"name": "Renamed again"})
        self.assertNotEqual(page.key, "website.explicit_key")
        self.assertTrue(page.key.startswith("website.renamed-again"), page.key)


@tagged("post_install", "-at_install")
class TestWebsiteFormAnswersJson(HttpCase):
    def _post_contact_form(self):
        page = self.url_open("/contactus").text
        csrf = re.search(r"csrf_token\W+([0-9a-f]{64}o\d+)", page)
        tree = html.fromstring(page)
        form = tree.xpath("//form[@data-model_name='mail.mail']")[0]
        data = {
            i.get("name"): i.get("value") or ""
            for i in form.xpath(".//input|.//textarea")
            if i.get("name")
        }
        data.update(
            name="Probe",
            email_from="probe@example.com",
            subject="Test",
            description="Test",
        )
        if csrf:
            data["csrf_token"] = csrf.group(1)
        return self.url_open("/website/form/mail.mail", data=data)

    def test_the_answer_is_typed_as_json_for_public_and_portal(self):
        res = self.url_open("/website/form/mail.mail", data={"subject": "x"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/json", res.headers.get("Content-Type", ""))
        self.assertNotIn("text/html", res.headers.get("Content-Type", ""))

        res = self._post_contact_form()
        self.assertIn("application/json", res.headers.get("Content-Type", ""))
        self.assertTrue(res.json().get("id"), res.text)

        new_test_user(
            self.env,
            login="form_portal",
            password="form_portal",
            groups="base.group_portal",
        )
        self.authenticate("form_portal", "form_portal")
        res = self._post_contact_form()
        self.assertIn("application/json", res.headers.get("Content-Type", ""))
        self.assertTrue(res.json().get("id"), res.text)


@tagged("post_install", "-at_install")
class TestFormSignatureTreatsEmptyRecipientAsAbsent(TransactionCase):
    def test_empty_and_absent_extra_recipients_sign_the_same(self):
        from odoo.addons.website.tools import website_form_signature_payload

        self.assertEqual(
            website_form_signature_payload("to@example.com", {"email_cc": ""}),
            website_form_signature_payload("to@example.com", {}),
        )
        self.assertNotEqual(
            website_form_signature_payload("to@example.com", {"email_cc": "cc@x.com"}),
            website_form_signature_payload("to@example.com", {}),
        )
