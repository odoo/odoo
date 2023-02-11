# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import tagged, users

@tagged('post_install', '-at_install')
class TestCRMLeadSmartCalendar(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestCRMLeadSmartCalendar, cls).setUpClass()
        # weekstart index : 7 (sunday), tz : UTC -4 / -5
        cls.user_NY_en_US = mail_new_test_user(
            cls.env, login='user_NY_en_US', lang='en_US', tz='America/New_York',
            name='user_NY_en_US User', email='user_NY_en_US@test.example.com',
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager,crm.group_use_lead')
        # weekstart index : 1 (monday), tz : UTC+0
        cls.env['res.lang']._activate_lang('pt_PT')
        cls.user_UTC_pt_PT = mail_new_test_user(
            cls.env, login='user_UTC_pt_PT', lang='pt_PT', tz='Europe/Lisbon',
            name='user_UTC_pt_PT User', email='user_UTC_pt_PT@test.example.com',
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager,crm.group_use_lead')

        cls.next_year = datetime.now().year + 1
        cls.calendar_meeting_1 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_1',
            'start': datetime(2020, 12, 13, 17),
            'stop': datetime(2020, 12, 13, 22)})
        cls.calendar_meeting_2 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_2',
            'start': datetime(2020, 12, 13, 2),
            'stop': datetime(2020, 12, 13, 3)})
        cls.calendar_meeting_3 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_3',
            'start': datetime(cls.next_year, 5, 4, 12),
            'stop': datetime(cls.next_year, 5, 4, 13)})
        cls.calendar_meeting_4 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_4',
            'allday': True,
            'start': datetime(2020, 12, 6, 0, 0, 0),
            'stop': datetime(2020, 12, 6, 23, 59, 59)})
        cls.calendar_meeting_5 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_5',
            'start': datetime(2020, 12, 13, 8),
            'stop': datetime(2020, 12, 13, 18),
            'allday': True})
        cls.calendar_meeting_6 = cls.env['calendar.event'].create({
            'name': 'calendar_meeting_6',
            'start': datetime(2020, 12, 12, 0),
            'stop': datetime(2020, 12, 19, 0)})

    @users('user_NY_en_US')
    def test_meeting_view_parameters_1(self):
        lead_smart_calendar_1 = self.env['crm.lead'].create({'name': 'Lead 1  - user_NY_en_US'})

        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, False)

        self.calendar_meeting_1.write({'opportunity_id': lead_smart_calendar_1.id})
        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(2020, 12, 13))

        self.calendar_meeting_2.write({'opportunity_id': lead_smart_calendar_1.id})
        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'month')
        self.assertEqual(initial_date, date(2020, 12, 12))

        self.calendar_meeting_3.write({'opportunity_id': lead_smart_calendar_1.id})
        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(self.next_year, 5, 4))

        lead_smart_calendar_2 = self.env['crm.lead'].create({'name': 'Lead 2 - user_NY_en_US'})

        self.calendar_meeting_4.write({'opportunity_id': lead_smart_calendar_2.id})
        mode, initial_date = lead_smart_calendar_2._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(2020, 12, 6))

        self.calendar_meeting_2.write({'opportunity_id': lead_smart_calendar_2.id})
        mode, initial_date = lead_smart_calendar_2._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(2020, 12, 6))

        self.calendar_meeting_5.write({'opportunity_id': lead_smart_calendar_2.id})
        mode, initial_date = lead_smart_calendar_2._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'month')
        self.assertEqual(initial_date, date(2020, 12, 6))

    @users('user_UTC_pt_PT')
    def test_meeting_view_parameters_2(self):

        lead_smart_calendar_1 = self.env['crm.lead'].create({'name': 'Lead 1 - user_UTC_pt_PT'})

        self.calendar_meeting_1.write({'opportunity_id': lead_smart_calendar_1.id})
        self.calendar_meeting_2.write({'opportunity_id': lead_smart_calendar_1.id})
        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(2020, 12, 13))

        self.calendar_meeting_3.write({'opportunity_id': lead_smart_calendar_1.id})
        mode, initial_date = lead_smart_calendar_1._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(self.next_year, 5, 4))

        lead_smart_calendar_2 = self.env['crm.lead'].create({'name': 'Lead 2 - user_UTC_pt_PT'})

        self.calendar_meeting_6.write({'opportunity_id': lead_smart_calendar_2.id})
        mode, initial_date = lead_smart_calendar_2._get_opportunity_meeting_view_parameters()
        self.assertEqual(mode, 'week')
        self.assertEqual(initial_date, date(2020, 12, 12))

    @users('user_sales_leads')
    def test_meeting_creation_from_lead_form(self):
        """ When going from a lead to the Calendar and adding a meeting, both salesman and customer
         should be attendees of the event """
        lead = self.env['crm.lead'].create({
            'name': 'SuperLead',
            'partner_id': self.contact_1.id,
        })
        calendar_action = lead.action_schedule_meeting()
        event = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'start': datetime(2020, 12, 13, 17),
            'stop': datetime(2020, 12, 13, 22),
        })
        self.assertEqual(len(event.attendee_ids), 2)
        self.assertIn(self.user_sales_leads.partner_id, event.attendee_ids.partner_id)
        self.assertIn(self.contact_1, event.attendee_ids.partner_id)
