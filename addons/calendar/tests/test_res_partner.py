# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests.common import new_test_user


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
        self.env['ir.rule'].create({'name': 'test_rule',
                                    'model_id': calendar_event_model_id,
                                    'domain_force': [('name', 'not in', ['event_9', 'event_10'])],
                                    'perm_read': True,
                                    'perm_create': False,
                                    'perm_write': False})
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
        """Ensure there's no AccessError raised when a user switched to sibling
        company requests to view a partner contact that has a scheduled meeting
        whose ancestor belongs to a company not visible in the current session.

        Scenario:
        - parent partner in company1, child partner in company1 (child.parent_id = parent)
        - create two users:
            * main_user & fake_user: has access to both companies, default company = company1
        - create a calendar event whose attendees are both users' partners
        - switch main_user to company2 and try to access the contact of the fake_user
        Expected: no AccessError and `meeting_count` for the child/restricted partner == 1
        """
        company1 = self.env.ref('base.main_company')
        company2 = self.env['res.company'].create({'name': 'OtherCompany'})

        parent = self.env['res.partner'].create({'name': 'Company A', 'company_id': company1.id})
        child = self.env['res.partner'].create({'name': 'test_user', 'company_id': company1.id, 'parent_id': parent.id})

        # users
        main_user = new_test_user(
            self.env, login='main_user', groups='base.group_user',
            company_id=company1.id, company_ids=[company1.id, company2.id]
        )
        fake_user = new_test_user(
            self.env, login='restricted_kanban_user', groups='base.group_user',
            company_id=company1.id, company_ids=[company1.id, company2.id]
        )
        fake_user.partner_id = child

        # create an event that includes both users' partners (imitates the provided payload)
        self.env['calendar.event'].create({
            'name': 'test',
            'start': '2026-02-16 17:00:00',
            'stop': '2026-02-16 18:00:00',
            'duration': 1,
            'allday': False,
            'partner_ids': [main_user.partner_id.id, fake_user.partner_id.id],
        })

        # Try to access the contact of fake_user, who has the scheduled meeting.
        spec = {
            'display_name': {},
            'parent_id': {'fields': {'display_name': {}}},
            'company_id': {'fields': {'display_name': {}}},
            'meeting_count': {},
        }
        vals = self.env['res.partner'].with_user(main_user).with_company(company2).browse(child.id).web_read(spec)
        self.assertTrue(vals)
        child_rec = vals[0]
        self.assertEqual(child_rec['id'], child.id)
        self.assertEqual(child_rec.get('meeting_count'), 1)
