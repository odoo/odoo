import logging
import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests import HttpCase, common, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website.models.website_visitor import WebsiteVisitor

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestVisitorState(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.visitor = self.env["website.visitor"].create({"access_token": "a" * 32})
        self.pages = self.env["website.page"].create(
            [
                {"name": name, "url": f"/{name}", "type": "qweb", "arch": "<div/>"}
                for name in ("visitor-first", "visitor-second")
            ]
        )

    def _track(self, page, **values):
        return self.env["website.track"].create(
            {
                "visitor_id": self.visitor.id,
                "page_id": page.id,
                "url": page.url,
                **values,
            }
        )

    def _upsert(self, **values):
        return self.visitor._upsert_visitor(
            self.visitor.access_token,
            lang_id=self.env.ref("base.lang_en").id,
            country_code="BE",
            website_id=self.env.ref("website.default_website").id,
            timezone="UTC",
            **values,
        )

    def test_statistics_follow_track_page_edits(self):
        track = self._track(self.pages[0])
        self.assertEqual(self.visitor.page_ids, self.pages[0])
        track.page_id = self.pages[1]
        _logger.debug("Track reassigned: pages=%s", self.visitor.page_ids.ids)
        self.assertEqual(self.visitor.page_ids, self.pages[1])

    def test_partner_merge_preserves_multiple_source_visitors(self):
        partners = self.env["res.partner"].create(
            [
                {"name": "Merge source one"},
                {"name": "Merge source two"},
                {"name": "Merge target"},
            ]
        )
        visitors = self.visitor.create(
            [{"access_token": str(partner.id)} for partner in partners[:2]]
        )
        tracks = self.env["website.track"].create(
            [
                {"visitor_id": visitor.id, "page_id": page.id, "url": page.url}
                for visitor, page in zip(visitors, self.pages, strict=True)
            ]
        )
        self.assertFalse(partners[2].visitor_ids)
        self.env["base.partner.merge.automatic.wizard"]._merge(
            partners.ids, partners[2]
        )
        survivor = partners[2].visitor_ids
        _logger.debug(
            "Merged source visitors=%s survivor=%s tracks=%s",
            visitors.ids,
            survivor.ids,
            survivor.website_track_ids.ids,
        )
        self.assertEqual(len(survivor), 1)
        self.assertEqual(survivor.access_token, str(partners[2].id))
        self.assertEqual(survivor.website_track_ids, tracks.sorted("id", reverse=True))
        self.assertEqual(survivor.page_ids, self.pages)

    def test_contact_manager_merge_preserves_scoped_visitor_data(self):
        manager = common.new_test_user(
            self.env,
            login="visitor_merge_manager",
            groups="base.group_user,base.group_partner_manager",
        )
        source, destination, unrelated = self.env["res.partner"].create(
            [
                {"name": name}
                for name in (
                    "Visitor source",
                    "Visitor destination",
                    "Unrelated visitor",
                )
            ]
        )
        source_visitor, other_visitor = self.env["website.visitor"].create(
            [{"access_token": str(partner.id)} for partner in (source, unrelated)]
        )
        self.assertFalse(source_visitor.with_user(manager).has_access("read"))
        track = self.env["website.track"].create(
            {"visitor_id": source_visitor.id, "url": "/merge-audit"}
        )
        self.env["base.partner.merge.automatic.wizard"].with_user(manager).create(
            {}
        )._merge(
            (source | destination).ids,
            destination.with_user(manager),
            extra_checks=False,
        )
        self.assertEqual(destination.visitor_ids, source_visitor)
        self.assertEqual(source_visitor.website_track_ids, track)
        self.assertEqual(source_visitor.access_token, str(destination.id))
        self.assertEqual(other_visitor.partner_id, unrelated)
        self.assertEqual(other_visitor.access_token, str(unrelated.id))
        _logger.debug(
            "Contact-manager merge: destination=%s visitor=%s unrelated=%s",
            destination.id,
            source_visitor.id,
            other_visitor.id,
        )

    def test_tracking_preserves_reusable_input_values(self):
        values = {"url": self.pages[0].url, "page_id": self.pages[0].id}
        expected = dict(values)
        domain = [("page_id", "=", self.pages[0].id)]
        self.visitor._add_tracking(domain, values)
        self.visitor._add_tracking(domain, values)
        _logger.debug(
            "Repeated tracking: values=%s tracks=%s",
            values,
            self.visitor.website_track_ids.ids,
        )
        self.assertEqual(len(self.visitor.website_track_ids), 1)
        self.assertEqual(values, expected)

    def test_page_search_agrees_with_displayed_pages(self):
        self._track(self.pages[0], url=False)
        self._track(self.pages[1])
        self._track(self.env["website.page"], url="/without-page")
        self.assertEqual(self.visitor.page_ids, self.pages[1])
        conditions = [
            ("in", self.pages[:1].ids, False),
            ("not in", self.pages[:1].ids, True),
            ("in", self.pages[1:].ids, True),
            ("not in", self.pages[1:].ids, False),
            ("=", False, False),
            ("!=", False, True),
            ("in", [False, self.pages[0].id], False),
            ("not in", [False, self.pages[0].id], True),
            ("ilike", "visitor-first", False),
            ("not ilike", "visitor-first", True),
            ("any", [("id", "=", self.pages[0].id)], False),
            ("not any", [("id", "=", self.pages[0].id)], True),
        ]
        for operator, value, expected in conditions:
            with self.subTest(operator=operator, value=value):
                result = self.visitor.search(
                    [("id", "=", self.visitor.id), ("page_ids", operator, value)]
                )
                _logger.debug(
                    "Page search %s %s -> %s expected=%s",
                    operator,
                    value,
                    result.ids,
                    expected,
                )
                self.assertEqual(bool(result), expected)

    def test_empty_page_search_ignores_url_less_tracks(self):
        self._track(self.pages[0], url=False)
        self.assertFalse(self.visitor.page_ids)
        found = self.visitor.search(
            [("id", "=", self.visitor.id), ("page_ids", "=", False)]
        )
        _logger.debug("Empty page search: result=%s", found.ids)
        self.assertEqual(found, self.visitor)

    def test_latest_page_breaks_timestamp_ties_by_track_id(self):
        for pages in (self.pages, self.pages[::-1]):
            with self.subTest(pages=pages.ids):
                self.visitor.website_track_ids.unlink()
                self._track(pages[0], visit_datetime="2026-01-01 12:00:00")
                newest = self._track(pages[1], visit_datetime="2026-01-01 12:00:00")
                self._track(pages[0], visit_datetime="2026-01-01 10:00:00")
                _logger.debug(
                    "Equal timestamps: latest=%s expected_track=%s page=%s",
                    self.visitor.last_visited_page_id.id,
                    newest.id,
                    pages[1].id,
                )
                self.assertEqual(self.visitor.last_visited_page_id, pages[1])

    def test_latest_page_batches_visitors_in_one_query(self):
        visitors = self.visitor | self.visitor.create(
            [{"access_token": f"batch-visitor-{index:018d}"} for index in range(9)]
        )
        self.env["website.track"].create(
            [
                {
                    "visitor_id": visitor.id,
                    "page_id": self.pages[0].id,
                    "url": self.pages[0].url,
                }
                for visitor in visitors
            ]
        )
        self.env.flush_all()
        visitors.invalidate_recordset(["last_visited_page_id"])
        with self.assertQueryCount(1):
            pages = visitors.mapped("last_visited_page_id")
        _logger.debug(
            "Batched last-page query: visitors=%s pages=%s", visitors.ids, pages.ids
        )
        self.assertEqual(pages, self.pages[0])

    def test_statistics_follow_track_url_edits(self):
        track = self._track(self.pages[0], url=False)
        self.assertEqual(self.visitor.visitor_page_count, 0)
        track.url = self.pages[0].url
        _logger.debug("Track URL populated: count=%s", self.visitor.visitor_page_count)
        self.assertEqual(self.visitor.visitor_page_count, 1)
        track.url = False
        self.assertEqual(self.visitor.visitor_page_count, 0)

    def test_latest_page_follows_timestamp_edits(self):
        first = self._track(self.pages[0], visit_datetime="2026-01-01 10:00:00")
        self._track(self.pages[1], visit_datetime="2026-01-01 11:00:00")
        self.assertEqual(self.visitor.last_visited_page_id, self.pages[1])
        first.visit_datetime = "2026-01-01 12:00:00"
        _logger.debug(
            "Track timestamp changed: latest=%s", self.visitor.last_visited_page_id.id
        )
        self.assertEqual(self.visitor.last_visited_page_id, self.pages[0])

    def test_last_visit_flushes_pending_values_and_updates_connection_state(self):
        self.visitor.last_connection_datetime = datetime.now() - timedelta(hours=9)
        self.assertFalse(self.visitor.is_connected)
        self.visitor._update_visitor_last_visit()
        _logger.debug(
            "Visit updated: count=%s connected=%s",
            self.visitor.visit_count,
            self.visitor.is_connected,
        )
        self.assertEqual(self.visitor.visit_count, 2)
        self.assertTrue(self.visitor.is_connected)

    def test_upsert_refreshes_cached_visitor_and_tracks(self):
        self.visitor.last_connection_datetime = datetime.now() - timedelta(hours=9)
        self.env.flush_all()
        self.assertFalse(self.visitor.is_connected)
        self.assertEqual(self.visitor.visit_count, 1)
        self.assertFalse(self.visitor.website_track_ids)
        self.assertFalse(self.visitor.timezone)
        self.assertEqual(self.visitor.visitor_page_count, 0)
        visitor_id, created = self._upsert(
            force_track_values={"url": self.pages[0].url, "page_id": self.pages[0].id}
        )
        _logger.debug(
            "Visitor upsert id=%s created=%s count=%s tracks=%s",
            visitor_id,
            created,
            self.visitor.visit_count,
            self.visitor.website_track_ids.ids,
        )
        self.assertEqual(visitor_id, self.visitor.id)
        self.assertFalse(created)
        self.assertEqual(self.visitor.visit_count, 2)
        self.assertTrue(self.visitor.is_connected)
        self.assertEqual(len(self.visitor.website_track_ids), 1)
        self.assertEqual(self.visitor.visitor_page_count, 1)
        self.assertEqual(self.visitor.timezone, "UTC")

    def test_upsert_refreshes_cached_partner_visitors(self):
        partner = self.env["res.partner"].create({"name": "Cached visitor owner"})
        self.assertFalse(partner.visitor_ids)
        visitor_id, created = self.visitor._upsert_visitor(
            partner.id,
            lang_id=False,
            country_code=False,
            website_id=False,
            timezone=False,
        )
        _logger.debug(
            "Inserted visitor=%s created=%s cached_owner_visitors=%s",
            visitor_id,
            created,
            partner.visitor_ids.ids,
        )
        self.assertTrue(created)
        self.assertEqual(partner.visitor_ids.ids, [visitor_id])

    def test_timezone_update_flushes_pending_value(self):
        self.visitor.timezone = "Europe/Brussels"
        self.visitor._update_visitor_timezone("Asia/Tokyo")
        _logger.debug("Timezone after SQL update: %s", self.visitor.timezone)
        self.assertEqual(self.visitor.timezone, "Asia/Tokyo")

    def test_missing_connection_date(self):
        self.visitor.last_connection_datetime = False
        _logger.debug(
            "Missing connection timestamp: connected=%s", self.visitor.is_connected
        )
        self.assertFalse(self.visitor.is_connected)
        self.assertFalse(self.visitor.time_since_last_action)

    def test_upsert_accepts_empty_optional_values(self):
        visitor_id, created = self.visitor._upsert_visitor(
            "b" * 32,
            lang_id=False,
            country_code=False,
            website_id=False,
            timezone=False,
        )
        visitor = self.visitor.browse(visitor_id)
        _logger.debug("Visitor created with empty optional values: id=%s", visitor_id)
        self.assertTrue(created)
        self.assertFalse(visitor.lang_id)
        self.assertFalse(visitor.country_id)
        self.assertFalse(visitor.website_id)
        self.assertFalse(visitor.timezone)


class MockVisitor(common.BaseCase):
    @contextmanager
    def mock_visitor_from_request(self, force_visitor=False):

        def _get_visitor_from_request(model, *args, **kwargs):
            return force_visitor

        with patch.object(
            WebsiteVisitor,
            "_get_visitor_from_request",
            autospec=True,
            wraps=WebsiteVisitor,
            side_effect=_get_visitor_from_request,
        ) as _get_visitor_from_request_mock:
            yield


@tagged("-at_install", "post_install", "website_visitor", "is_query_count")
class WebsiteVisitorTestsCommon(MockVisitor, HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.website = self.env["website"].search(
            [("company_id", "=", self.env.user.company_id.id)], limit=1
        )

        untracked_view = self.env["ir.ui.view"].create(
            {
                "name": "UntackedView",
                "type": "qweb",
                "arch": """<t name="Homepage" t-name="test.untracked_page">
                        <t t-call="website.layout">
                            I am a generic page²
                        </t>
                    </t>""",
                "key": "test.untracked_page",
                "track": False,
            }
        )
        tracked_view = self.env["ir.ui.view"].create(
            {
                "name": "TrackedView",
                "type": "qweb",
                "arch": """<t name="Homepage" t-name="test.tracked_page">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>""",
                "key": "test.tracked_page",
                "track": True,
            }
        )
        tracked_view_2 = self.env["ir.ui.view"].create(
            {
                "name": "TrackedView2",
                "type": "qweb",
                "arch": """<t name="OtherPage" t-name="test.tracked_page_2">
                        <t t-call="website.layout">
                            I am a generic second page
                        </t>
                    </t>""",
                "key": "test.tracked_page_2",
                "track": True,
            }
        )
        [self.untracked_page, self.tracked_page, self.tracked_page_2] = self.env[
            "website.page"
        ].create(
            [
                {
                    "view_id": untracked_view.id,
                    "url": "/untracked_view",
                    "website_published": True,
                },
                {
                    "view_id": tracked_view.id,
                    "url": "/tracked_view",
                    "website_published": True,
                },
                {
                    "view_id": tracked_view_2.id,
                    "url": "/tracked_view_2",
                    "website_published": True,
                },
            ]
        )

        self.user_portal = self.env["res.users"].search([("login", "=", "portal")])
        self.partner_portal = self.user_portal.partner_id
        if not self.user_portal:
            self.env["ir.config_parameter"].sudo().set_param(
                "auth_password_policy.minlength", 4
            )
            self.partner_portal = self.env["res.partner"].create(
                {
                    "name": "Joel Willis",
                    "email": "joel.willis63@example.com",
                }
            )
            self.user_portal = self.env["res.users"].create(
                {
                    "login": "portal",
                    "password": "portal",
                    "partner_id": self.partner_portal.id,
                    "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        self.partner_admin_duplicate = self.env["res.partner"].create(
            {"name": "Mitchell"}
        )

    def _get_last_visitor(self):
        return self.env["website.visitor"].search([], limit=1, order="id DESC")

    def assertPageTracked(self, visitor, page):
        self.assertIn(page, visitor.website_track_ids.page_id)
        self.assertIn(page, visitor.page_ids)

    def assertVisitorTracking(self, visitor, pages):
        for page in pages:
            self.assertPageTracked(visitor, page)
        self.assertEqual(len(visitor.website_track_ids), len(pages))

    def assertVisitorDeactivated(self, visitor, main_visitor):
        self.assertFalse(visitor.exists(), "The anonymous visitor should be deleted")
        self.assertTrue(visitor.website_track_ids < main_visitor.website_track_ids)

    def _test_unlink_old_visitors(self, inactive_visitors, active_visitors):
        WebsiteVisitor = self.env["website.visitor"]

        self.env["ir.config_parameter"].sudo().set_param("website.visitor.live.days", 7)

        with self.assertQueryCount(2):
            WebsiteVisitor.search(WebsiteVisitor._get_domain_inactive_visitors())

        inactive_visitor_ids = inactive_visitors.ids
        active_visitor_ids = active_visitors.ids

        self.env.ref("website.website_visitor_cron").method_direct_trigger()
        if inactive_visitor_ids:
            self.assertFalse(
                bool(WebsiteVisitor.search([("id", "in", inactive_visitor_ids)]))
            )
        if active_visitor_ids:
            self.assertEqual(
                active_visitors,
                WebsiteVisitor.search([("id", "in", active_visitor_ids)]),
            )

    def _prepare_main_visitor_data(self):
        return {
            "lang_id": self.env.ref("base.lang_en").id,
            "country_id": self.env.ref("base.be").id,
            "website_id": 1,
            "access_token": self.partner_admin.id,
            "website_track_ids": [
                (0, 0, {"page_id": self.tracked_page.id, "url": self.tracked_page.url})
            ],
        }

    def _prepare_linked_visitor_data(self):
        return {
            "lang_id": self.env.ref("base.lang_en").id,
            "country_id": self.env.ref("base.be").id,
            "website_id": 1,
            "access_token": "%032x" % random.randrange(16**32),
            "website_track_ids": [
                (
                    0,
                    0,
                    {"page_id": self.tracked_page_2.id, "url": self.tracked_page_2.url},
                )
            ],
        }

    def _authenticate_via_web(self, login, pwd):
        res = self.url_open("/web/login")
        csrf_anchor = '<input type="hidden" name="csrf_token" value="'
        self.url_open(
            "/web/login",
            timeout=200,
            data={
                "login": login,
                "password": pwd,
                "csrf_token": res.text.partition(csrf_anchor)[2].partition('"')[0],
            },
        )


class WebsiteVisitorTests(WebsiteVisitorTestsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_registry_readonly_mode(False)

    def test_visitor_creation_on_tracked_page(self):
        existing_visitors = self.env["website.visitor"].search([])
        existing_tracks = self.env["website.track"].search([])
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page.url)
        self.url_open(self.tracked_page.url)

        new_visitor = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        new_track = self.env["website.track"].search(
            [("id", "not in", existing_tracks.ids)]
        )
        self.assertEqual(len(new_visitor), 1, "1 visitor should be created")
        self.assertEqual(len(new_track), 2, "There should be 2 tracked page")
        self.assertEqual(new_visitor.visit_count, 1)
        self.assertEqual(new_visitor.website_track_ids, new_track)
        self.assertVisitorTracking(new_visitor, self.tracked_page + self.tracked_page)

        self._authenticate_via_web(self.user_admin.login, "admin")

        visitor_admin = new_visitor
        self.url_open(self.tracked_page_2.url)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(
            len(new_visitors), 1, "There should still be only one visitor."
        )
        self.assertVisitorTracking(
            visitor_admin, self.tracked_page + self.tracked_page + self.tracked_page_2
        )
        self.assertEqual(visitor_admin.partner_id, self.partner_admin)
        self.assertEqual(visitor_admin.name, self.partner_admin.name)

        self.url_open("/web/session/logout")
        self._authenticate_via_web(self.user_portal.login, "portal")

        self.assertFalse(
            self.env["website.visitor"].search(
                [("id", "not in", (existing_visitors | visitor_admin).ids)]
            ),
            "No extra visitor should be created",
        )

        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(len(new_visitors), 2, "One extra visitor should be created")
        visitor_portal = new_visitors[0]
        self.assertEqual(visitor_portal.partner_id, self.partner_portal)
        self.assertEqual(visitor_portal.name, self.partner_portal.name)
        self.assertVisitorTracking(
            visitor_portal, self.tracked_page | self.tracked_page_2
        )

        self.url_open("/web/session/logout")

        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous = new_visitors[0]
        self.assertFalse(visitor_anonymous.name)
        self.assertFalse(visitor_anonymous.partner_id)
        self.assertVisitorTracking(
            visitor_anonymous, self.tracked_page | self.tracked_page_2
        )
        visitor_anonymous_tracks = visitor_anonymous.website_track_ids

        self._authenticate_via_web(self.user_admin.login, "admin")

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(new_visitors, visitor_admin | visitor_portal)
        visitor_admin = self.env["website.visitor"].search(
            [("partner_id", "=", self.partner_admin.id)]
        )
        self.assertTrue(visitor_anonymous_tracks < visitor_admin.website_track_ids)
        self.assertEqual(
            len(visitor_admin.website_track_ids),
            5,
            "There should be 5 tracked page for the admin",
        )

        self.url_open("/web/session/logout")

        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous_2 = new_visitors[0]
        self.assertFalse(visitor_anonymous_2.name)
        self.assertFalse(visitor_anonymous_2.partner_id)
        self.assertVisitorTracking(
            visitor_anonymous_2, self.tracked_page | self.tracked_page_2
        )
        visitor_anonymous_2_tracks = visitor_anonymous_2.website_track_ids

        self._authenticate_via_web(self.user_portal.login, "portal")

        new_visitors = self.env["website.visitor"].search(
            [("id", "not in", existing_visitors.ids)]
        )
        self.assertEqual(new_visitors, visitor_admin | visitor_portal)
        self.assertTrue(visitor_anonymous_2_tracks < visitor_portal.website_track_ids)
        self.assertEqual(
            len(visitor_portal.website_track_ids),
            4,
            "There should be 4 tracked page for the portal user",
        )

        for track in visitor_portal.website_track_ids:
            track.write(
                {"visit_datetime": track.visit_datetime - timedelta(minutes=30)}
            )

        self.url_open(self.tracked_page.url)
        visitor_portal.invalidate_model(["website_track_ids"])
        self.assertEqual(
            len(visitor_portal.website_track_ids),
            5,
            "There should be 5 tracked page for the portal user",
        )

        visitor_portal.write(
            {
                "last_connection_datetime": visitor_portal.last_connection_datetime
                - timedelta(hours=9)
            }
        )
        self.url_open(self.tracked_page.url)
        visitor_portal.invalidate_model(["visit_count"])
        self.assertEqual(
            visitor_portal.visit_count,
            2,
            "There should be 2 visits for the portal user",
        )

    def test_update_last_visit_8h_increment(self):
        visitor = self.env["website.visitor"].create(
            {
                "lang_id": self.env.ref("base.lang_en").id,
                "website_id": 1,
                "access_token": "e9d2b14b21be669518b14a9590cb62ff",
            }
        )
        start = visitor.visit_count
        self.env.cr.execute(
            "UPDATE website_visitor "
            "SET last_connection_datetime = (now() at time zone 'UTC') - INTERVAL '9 hours' "
            "WHERE id = %s",
            (visitor.id,),
        )
        visitor.invalidate_recordset()

        visitor._update_visitor_last_visit()
        visitor.invalidate_recordset()
        self.assertEqual(
            visitor.visit_count, start + 1, "a visit after 8h must increment"
        )

        visitor._update_visitor_last_visit()
        visitor.invalidate_recordset()
        self.assertEqual(
            visitor.visit_count, start + 1, "a visit within 8h must not increment"
        )

    def test_clean_inactive_visitors(self):
        inactive_visitors = self.env["website.visitor"].create(
            [
                {
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "last_connection_datetime": datetime.now() - timedelta(days=8),
                    "access_token": "f9d2b14b21be669518b14a9590cb62ed",
                },
                {
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "last_connection_datetime": datetime.now() - timedelta(days=15),
                    "access_token": "f9d2d261a725da7f596574ca84e52f47",
                },
            ]
        )

        active_visitors = self.env["website.visitor"].create(
            [
                {
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "last_connection_datetime": datetime.now() - timedelta(days=1),
                    "access_token": "f9d2526d9c15658bdc91d2119e54b554",
                },
                {
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "partner_id": self.partner_demo.id,
                    "last_connection_datetime": datetime.now() - timedelta(days=15),
                    "access_token": self.partner_demo.id,
                },
            ]
        )

        self._test_unlink_old_visitors(inactive_visitors, active_visitors)

    def test_link_to_visitor(self):
        [main_visitor, linked_visitor] = self.env["website.visitor"].create(
            [self._prepare_main_visitor_data(), self._prepare_linked_visitor_data()]
        )
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

    def test_merge_partner_with_visitor_both(self):
        Visitor = self.env["website.visitor"]
        (self.partner_admin_duplicate + self.partner_admin).visitor_ids.unlink()
        [visitor_admin_duplicate, visitor_admin] = Visitor.create(
            [
                {
                    "partner_id": self.partner_admin_duplicate.id,
                    "access_token": self.partner_admin_duplicate.id,
                },
                {
                    "partner_id": self.partner_admin.id,
                    "access_token": self.partner_admin.id,
                },
            ]
        )
        self.assertTrue(
            visitor_admin_duplicate.partner_id.id
            == int(visitor_admin_duplicate.access_token)
            == self.partner_admin_duplicate.id
        )
        self.assertTrue(
            visitor_admin.partner_id.id
            == int(visitor_admin.access_token)
            == self.partner_admin.id
        )

        self.env["website.track"].create(
            [
                {
                    "visitor_id": visitor_admin_duplicate.id,
                    "url": "/admin/about-duplicate",
                },
                {"visitor_id": visitor_admin.id, "url": "/admin"},
            ]
        )
        self.assertEqual(
            visitor_admin_duplicate.website_track_ids.url, "/admin/about-duplicate"
        )
        self.assertEqual(visitor_admin.website_track_ids.url, "/admin")

        self.env["base.partner.merge.automatic.wizard"]._merge(
            (self.partner_admin + self.partner_admin_duplicate).ids, self.partner_admin
        )
        self.assertTrue(visitor_admin.exists())
        self.assertFalse(visitor_admin_duplicate.exists())
        self.assertFalse(
            Visitor.search_count(
                [("partner_id", "=", self.partner_admin_duplicate.id)]
            ),
            "The admin_duplicate visitor should've been merged (and deleted) with the admin one.",
        )
        self.assertEqual(
            visitor_admin.website_track_ids.sorted("url").mapped("url"),
            ["/admin", "/admin/about-duplicate"],
        )

    def test_merge_partner_with_visitor_single(self):
        Visitor = self.env["website.visitor"]
        (self.partner_admin_duplicate + self.partner_admin).visitor_ids.unlink()
        visitor_admin_duplicate = Visitor.create(
            {
                "partner_id": self.partner_admin_duplicate.id,
                "access_token": self.partner_admin_duplicate.id,
            }
        )
        self.assertTrue(
            visitor_admin_duplicate.partner_id.id
            == int(visitor_admin_duplicate.access_token)
            == self.partner_admin_duplicate.id
        )

        self.env["base.partner.merge.automatic.wizard"]._merge(
            (self.partner_admin + self.partner_admin_duplicate).ids, self.partner_admin
        )
        self.assertTrue(
            visitor_admin_duplicate.partner_id.id
            == int(visitor_admin_duplicate.access_token)
            == self.partner_admin.id,
            "The admin_duplicate visitor should now be linked to the admin partner.",
        )
        self.assertFalse(
            Visitor.search_count(
                [("partner_id", "=", self.partner_admin_duplicate.id)]
            ),
            "The admin_duplicate visitor should've been merged (and deleted) with the admin one.",
        )


@tagged("-at_install", "post_install")
class TestPortalWizardMultiWebsites(HttpCase):
    def setUp(self):
        super().setUp()
        self.website = self.env["website"].create(
            {
                "name": "website_specific_user_account",
                "specific_user_account": True,
            }
        )
        self.other_website = self.env["website"].create(
            {
                "name": "other_website_specific_user_account",
                "specific_user_account": True,
            }
        )
        self.email_address = "email_address@example.com"
        partner_specific = self.env["res.partner"].create(
            {
                "name": "partner_specific",
                "email": self.email_address,
                "website_id": self.website.id,
            }
        )
        partner_all_websites = self.env["res.partner"].create(
            {
                "name": "partner_all_websites",
                "email": self.email_address,
            }
        )
        self.portal_user_specific = self._create_portal_user(partner_specific)
        self.portal_user_specific.action_grant_access()
        self.assertTrue(self.portal_user_specific.is_portal)
        self.portal_user_all_websites = self._create_portal_user(partner_all_websites)

    def test_portal_wizard_multi_websites_1(self):
        partner_specific_other_website = self.env["res.partner"].create(
            {
                "name": "partner_specific_other_website",
                "email": self.email_address,
                "website_id": self.other_website.id,
            }
        )
        portal_user_specific_other_website = self._create_portal_user(
            partner_specific_other_website
        )
        self.assertEqual(portal_user_specific_other_website.email_state, "ok")

    def test_portal_wizard_multi_websites_2(self):
        partner_specific_same_website = self.env["res.partner"].create(
            {
                "name": "partner_specific_same_website",
                "email": self.email_address,
                "website_id": self.website.id,
            }
        )
        portal_user_specific_same_website = self._create_portal_user(
            partner_specific_same_website
        )
        self.assertEqual(portal_user_specific_same_website.email_state, "exist")

    def test_portal_wizard_multi_websites_3(self):
        self.assertEqual(self.portal_user_all_websites.email_state, "ok")

    def test_portal_wizard_multi_websites_4(self):
        other_email_address = "other_email_address@example.com"
        partner_specific_other_website = self.env["res.partner"].create(
            {
                "name": "partner_specific_other_website",
                "email": other_email_address,
                "website_id": self.other_website.id,
            }
        )
        portal_user_specific_other_website = self._create_portal_user(
            partner_specific_other_website
        )
        partner_all_websites = self.env["res.partner"].create(
            {
                "name": "partner_all_websites",
                "email": other_email_address,
            }
        )
        portal_user_all_websites_other_address = self._create_portal_user(
            partner_all_websites
        )
        portal_user_all_websites_other_address.action_grant_access()
        self.assertTrue(portal_user_all_websites_other_address.is_portal)
        self.assertEqual(portal_user_specific_other_website.email_state, "ok")

    def test_portal_wizard_multi_websites_5(self):
        partner_all_websites_second = self.env["res.partner"].create(
            {
                "name": "partner_all_websites_second",
                "email": self.email_address,
            }
        )
        portal_user_all_websites_second = self._create_portal_user(
            partner_all_websites_second
        )
        self.portal_user_all_websites.action_grant_access()
        self.assertTrue(self.portal_user_all_websites.is_portal)
        self.assertEqual(portal_user_all_websites_second.email_state, "exist")

    def test_portal_wizard_multi_websites_6(self):
        partner_specific_current_website = self.env["res.partner"].create(
            {
                "name": "partner_specific_current_website",
                "email": self.email_address,
                "website_id": self.env["website"].get_current_website().id,
            }
        )
        portal_user_specific_current_website = self._create_portal_user(
            partner_specific_current_website
        )
        portal_user_specific_current_website.action_grant_access()
        self.assertTrue(portal_user_specific_current_website.is_portal)
        self.assertEqual(self.portal_user_all_websites.email_state, "exist")

    def _create_portal_user(self, partner):
        portal_wizard = (
            self.env["portal.wizard"].with_context(active_ids=[partner.id]).create({})
        )
        return portal_wizard.user_ids
