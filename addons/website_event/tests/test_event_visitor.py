import logging
from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon
from odoo.addons.website_event.tests.common import TestEventOnlineCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestVisitorRegistrationMerge(TransactionCase):
    def test_merge_assigns_only_unlinked_registration_partners(self):
        partners = self.env["res.partner"].create(
            [
                {"name": "Visitor contact"},
                {"name": "Existing attendee"},
            ]
        )
        target, source = self.env["website.visitor"].create(
            [
                {"access_token": str(partners[0].id)},
                {"access_token": "e" * 32},
            ]
        )
        event = self.env["event.event"].create(
            {
                "name": "Visitor merge event",
                "date_begin": "2026-10-01 10:00:00",
                "date_end": "2026-10-01 12:00:00",
            }
        )
        unlinked, linked = self.env["event.registration"].create(
            [
                {
                    "event_id": event.id,
                    "visitor_id": source.id,
                    "partner_id": partner_id,
                    "name": "Attendee",
                }
                for partner_id in (False, partners[1].id)
            ]
        )
        source._merge_visitor(target)
        _logger.debug(
            "Merged registrations: visitor=%s assigned_partner=%s preserved_partner=%s",
            target.id,
            unlinked.partner_id.id,
            linked.partner_id.id,
        )
        self.assertEqual(unlinked.visitor_id, target)
        self.assertEqual(linked.visitor_id, target)
        self.assertEqual(unlinked.partner_id, partners[0])
        self.assertEqual(linked.partner_id, partners[1])
        self.assertFalse(source.exists())


@tagged("website_visitor", "is_query_count")
class TestEventVisitor(TestEventOnlineCommon, WebsiteVisitorTestsCommon):
    def test_clean_inactive_visitors_event(self):
        active_visitors = self.env["website.visitor"].create(
            [
                {
                    "lang_id": self.env.ref("base.lang_en").id,
                    "country_id": self.env.ref("base.be").id,
                    "website_id": 1,
                    "last_connection_datetime": datetime.now() - timedelta(days=8),
                    "access_token": "f9d2af99f543874642f89bd334fa4a49",
                    "event_registration_ids": [(0, 0, {"event_id": self.event_0.id})],
                }
            ]
        )

        self._test_unlink_old_visitors(self.env["website.visitor"], active_visitors)

    def test_registration_desk_ir_rule_scoping(self):
        """Round-1 fix WEM-04: a registration-desk user must only read
        visitors linked to an event registration, not every visitor."""
        desk_user = mail_new_test_user(
            self.env,
            login="user_registration_desk",
            groups="event.group_event_registration_desk",
        )
        registered_visitor, unregistered_visitor = self.env["website.visitor"].create(
            [
                {
                    "access_token": "a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
                    "event_registration_ids": [(0, 0, {"event_id": self.event_0.id})],
                },
                {"access_token": "b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2"},
            ]
        )

        registered_visitor.with_user(desk_user).read(["id"])

        with self.assertRaises(AccessError):
            unregistered_visitor.with_user(desk_user).read(["id"])

    def test_link_to_visitor_event(self):
        [main_visitor, linked_visitor] = self.env["website.visitor"].create(
            [self._prepare_main_visitor_data(), self._prepare_linked_visitor_data()]
        )

        event_1 = self.env["event.event"].create(
            {
                "name": "OtherEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        linked_visitor.write(
            {"event_registration_ids": [(0, 0, {"event_id": event_1.id})]}
        )

        self.assertEqual(self.event_0, main_visitor.event_registered_ids)
        self.assertEqual(event_1, linked_visitor.event_registered_ids)

        linked_visitor._merge_visitor(main_visitor)
        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        self.assertEqual(self.event_0 | event_1, main_visitor.event_registered_ids)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        values.update(
            {"event_registration_ids": [(0, 0, {"event_id": self.event_0.id})]}
        )
        return values
