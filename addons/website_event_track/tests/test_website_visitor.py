import logging
import runpy
from datetime import datetime, timedelta
from pathlib import Path

from odoo.tests import TransactionCase, tagged

from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon
from odoo.addons.website_event.tests.common import TestEventOnlineCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestTrackVisitorIdentity(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partners = self.env["res.partner"].create(
            [
                {"name": "Identified visitor"},
                {"name": "Explicit attendee"},
            ]
        )
        self.visitor = self.env["website.visitor"].create({"access_token": "c" * 32})
        event = self.env["event.event"].create(
            {
                "name": "Identity event",
                "date_begin": "2026-10-01 10:00:00",
                "date_end": "2026-10-01 12:00:00",
            }
        )
        track = self.env["event.track"].create(
            {"name": "Identity track", "event_id": event.id}
        )
        self.links = self.env["event.track.visitor"].create(
            [
                {
                    "visitor_id": self.visitor.id,
                    "track_id": track.id,
                    "partner_id": partner_id,
                }
                for partner_id in (False, self.partners[1].id)
            ]
        )

    def _assert_partners(self):
        _logger.debug(
            "Track visitor partners: visitor=%s partners=%s",
            self.links.visitor_id.ids,
            self.links.partner_id.ids,
        )
        self.assertEqual(self.links[0].partner_id, self.partners[0])
        self.assertEqual(self.links[1].partner_id, self.partners[1])

    def test_identification_assigns_only_missing_partners(self):
        self.assertFalse(self.links[0].partner_id)
        self.visitor.access_token = str(self.partners[0].id)
        self._assert_partners()

    def test_merge_assigns_only_missing_partners(self):
        target = self.visitor.create({"access_token": str(self.partners[0].id)})
        self.visitor._merge_visitor(target)
        self.assertEqual(self.links.visitor_id, target)
        self._assert_partners()

    def test_partner_backfill_is_idempotent_and_preserves_explicit_partner(self):
        self.visitor.access_token = str(self.partners[0].id)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE event_track_visitor SET partner_id = NULL WHERE id = %s",
            [self.links[0].id],
        )
        migration = runpy.run_path(
            str(
                Path(__file__).resolve().parents[1]
                / "migrations/1.5/post-backfill_visitor_partners.py"
            )
        )["migrate"]
        migration(self.env.cr, "19.0.1.4")
        first_count = self.env.cr.rowcount
        migration(self.env.cr, "19.0.1.4")
        _logger.debug(
            "Repeated partner backfill: first=%s second=%s",
            first_count,
            self.env.cr.rowcount,
        )
        self.assertGreaterEqual(first_count, 1)
        self.assertEqual(self.env.cr.rowcount, 0)
        self.links.invalidate_recordset(["partner_id"])
        self._assert_partners()


@tagged("website_visitor", "is_query_count")
class WebsiteVisitorTestsEventTrack(TestEventOnlineCommon, WebsiteVisitorTestsCommon):
    def test_clean_inactive_visitors_event_track(self):
        track_1 = self.env["event.track"].create(
            {
                "name": "Track 1",
                "event_id": self.event_0.id,
            }
        )

        active_visitors = self.env["website.visitor"].create(
            [
                {
                    "name": "Wishlister Alex",
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "last_connection_datetime": datetime.now() - timedelta(days=8),
                    "access_token": "f9d2b93591d6f602e5e8afa238e35a6c",
                    "event_track_visitor_ids": [
                        (0, 0, {"track_id": track_1.id, "is_wishlisted": True})
                    ],
                }
            ]
        )

        self._test_unlink_old_visitors(self.env["website.visitor"], active_visitors)

    def test_link_to_visitor_event_track(self):

        [track_1, track_2] = self.env["event.track"].create(
            [
                {
                    "name": "Track 1",
                    "event_id": self.event_0.id,
                },
                {
                    "name": "Track 2",
                    "event_id": self.event_0.id,
                },
            ]
        )

        [main_visitor, linked_visitor] = self.env["website.visitor"].create(
            [self._prepare_main_visitor_data(), self._prepare_linked_visitor_data()]
        )

        self.env["event.track.visitor"].create(
            [
                {
                    "visitor_id": main_visitor.id,
                    "track_id": track_1.id,
                    "is_wishlisted": True,
                },
                {
                    "visitor_id": linked_visitor.id,
                    "track_id": track_2.id,
                    "is_wishlisted": True,
                },
            ]
        )

        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        self.assertEqual(main_visitor.event_track_wishlisted_ids, track_1 | track_2)
