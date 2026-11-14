# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import new_test_user, tagged, TransactionCase
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResPartner(TransactionCase):

    def test_meeting_count(self):
        test_user = new_test_user(self.env, login='test_user', groups='base.group_user, base.group_partner_manager')
        Partner = self.env['res.partner'].with_user(test_user)
        Event = self.env['calendar.event'].with_user(test_user)

        # Partner hierarchy
        #     1       5
        #    /|
        #   2 3
        #     |
        #     4

        test_partner_1 = Partner.create({'name': 'test_partner_1'})
        test_partner_2 = Partner.create({'name': 'test_partner_2', 'parent_id': test_partner_1.id})
        test_partner_3 = Partner.create({'name': 'test_partner_3', 'parent_id': test_partner_1.id})
        test_partner_4 = Partner.create({'name': 'test_partner_4', 'parent_id': test_partner_3.id})
        test_partner_5 = Partner.create({'name': 'test_partner_5'})
        test_partner_6 = Partner.create({'name': 'test_partner_6'})
        test_partner_7 = Partner.create({'name': 'test_partner_7', 'parent_id': test_partner_6.id})

        Event.create({'name': 'event_1',
                      'partner_ids': [(6, 0, [test_partner_1.id,
                                              test_partner_2.id,
                                              test_partner_3.id,
                                              test_partner_4.id])]})
        Event.create({'name': 'event_2',
                      'partner_ids': [(6, 0, [test_partner_1.id,
                                              test_partner_3.id])]})
        Event.create({'name': 'event_2',
                      'partner_ids': [(6, 0, [test_partner_2.id,
                                              test_partner_3.id])]})
        Event.create({'name': 'event_3',
                      'partner_ids': [(6, 0, [test_partner_3.id,
                                              test_partner_4.id])]})
        Event.create({'name': 'event_4',
                      'partner_ids': [(6, 0, [test_partner_1.id])]})
        Event.create({'name': 'event_5',
                      'partner_ids': [(6, 0, [test_partner_3.id])]})
        Event.create({'name': 'event_6',
                      'partner_ids': [(6, 0, [test_partner_4.id])]})
        Event.create({'name': 'event_7',
                      'partner_ids': [(6, 0, [test_partner_5.id])]})
        Event.create({'name': 'event_8',
                      'partner_ids': [(6, 0, [test_partner_5.id,
                                              test_partner_7.id])]})

        #Test rule to see if ir.rules are applied
        calendar_event_model_id = self.env['ir.model']._get('calendar.event').id
        self.env['ir.access'].create({
            'name': 'test_rule',
            'model_id': calendar_event_model_id,
            'operation': 'r',
            'domain': [('name', 'not in', ['event_9', 'event_10'])],
        })

        # create generally requires read -> prevented by above test rule
        Event.sudo().create({'name': 'event_9',
                      'partner_ids': [(6, 0, [test_partner_2.id,
                                              test_partner_3.id])]})

        Event.sudo().create({'name': 'event_10',
                      'partner_ids': [(6, 0, [test_partner_5.id])]})

        self.assertEqual(test_partner_1.meeting_count, 7)
        self.assertEqual(test_partner_2.meeting_count, 2)
        self.assertEqual(test_partner_3.meeting_count, 6)
        self.assertEqual(test_partner_4.meeting_count, 3)
        self.assertEqual(test_partner_5.meeting_count, 2)
        self.assertEqual(test_partner_6.meeting_count, 1)
        self.assertEqual(test_partner_7.meeting_count, 1)

    def test_view_multicompany_contact_with_inaccessible_meeting_parent(self):
        """Check the partner's meeting accesses in a multi-company environment."""

        company1 = self.env.ref('base.main_company')
        company2 = self.env['res.company'].create({'name': 'OtherCompany'})

        company1.partner_id.company_id = company1

        # create two users
        allcompany_user = mail_new_test_user(
            self.env,
            name='All company User',
            login='allcompany_user',
            company_id=company1.id,
            company_ids=[company1.id, company2.id],
            groups='base.group_user',
        )
        company1_user = mail_new_test_user(
            self.env,
            name='Restricted Kanban User',
            login='restricted_kanban_user',
            company_id=company1.id,
            company_ids=[company1.id, company2.id],
            groups='base.group_user',
        )
        company1_user.partner_id.write({'company_id': company1.id, 'parent_id': company1.partner_id.id})

        # create an event that includes both users' partners (imitates the provided payload)
        self.env['calendar.event'].create({
            'name': 'test',
            'start': '2026-02-16 17:00:00',
            'stop': '2026-02-16 18:00:00',
            'partner_ids': [allcompany_user.partner_id.id, company1_user.partner_id.id],
        })

        # compute the meeting_count as seen from another company
        self.env.invalidate_all()
        c1_partner_seen_from_c2 = company1_user.partner_id.with_user(allcompany_user).with_company(company2)
        self.assertEqual(c1_partner_seen_from_c2.meeting_count, 1, "Should compute meeting count without access error as partner is accessible in all companies")

    @freeze_time("2025-04-08 12:00:00")
    def test_in_meeting_until(self):
        event = self.env["calendar.event"].create({
            "name": "Meeting",
            "start": fields.Datetime.now(),
            "stop": fields.Datetime.now() + relativedelta(hours=1),
            "show_as": "busy",
            "privacy": "public",
        })
        self.assertEqual(self.env.user.partner_id.meeting_until, event.stop)

    @freeze_time("2025-04-08 12:00:00")
    def test_in_meeting_until_filters(self):
        """Only accepted, busy, public and non all-day meetings are taken into account."""
        now = fields.Datetime.now()
        cases = [
            ("private", {"privacy": "private"}, "accepted"),
            ("available", {"show_as": "free"}, "accepted"),
            ("all day", {"allday": True, "start_date": now.date(), "stop_date": now.date()}, "accepted"),
            ("declined", {}, "declined"),
            ("tentative", {}, "tentative"),
            ("needs action", {}, "needsAction"),
        ]
        for description, values, state in cases:
            with self.subTest(description=description):
                partner = self.env["res.partner"].create({"name": description})
                event = self.env["calendar.event"].create({
                    "name": "Meeting",
                    "start": now,
                    "stop": now + relativedelta(hours=1),
                    "show_as": "busy",
                    "privacy": "public",
                    "partner_ids": [partner.id],
                    **values,
                })
                event.attendee_ids.state = state
                self.assertFalse(partner.meeting_until)

    @freeze_time("2025-04-08 12:00:00")
    def test_in_meeting_until_back_to_back(self):
        """Back-to-back meetings extend meeting_until, a gap between meetings stops it."""
        now = fields.Datetime.now()
        self.env["calendar.event"].create([{
            "name": f"Meeting {start}",
            "start": now + relativedelta(hours=start),
            "stop": now + relativedelta(hours=start + 1),
            "show_as": "busy",
            "privacy": "public",
        } for start in (0, 1, 3)])
        self.assertEqual(self.env.user.partner_id.meeting_until, now + relativedelta(hours=2))
