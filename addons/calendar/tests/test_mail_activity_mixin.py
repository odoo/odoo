# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

import pytz

from odoo import Command
from odoo import tests
from odoo.addons.mail.tests.common import MailCommon


@tests.tagged('mail_activity_mixin')
class TestMailActivityMixin(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailActivityMixin, cls).setUpClass()
        # using res.partner as the model inheriting from mail.activity.mixin
        cls.test_record = cls.env['res.partner'].with_context(cls._test_context).create({'name': 'Test'})
        cls.activity_type_1 = cls.env['mail.activity.type'].create({
            'name': 'Calendar Activity Test Default',
            'summary': 'default activity',
            'res_model': 'res.partner',
        })
        cls.env['ir.model.data'].create({
            'name': cls.activity_type_1.name.lower().replace(' ', '_'),
            'module': 'calendar',
            'model': cls.activity_type_1._name,
            'res_id': cls.activity_type_1.id,
        })
        # reset ctx
        cls._reset_mail_context(cls.test_record)

    def test_activity_calendar_event_id(self):
        """Test the computed field "activity_calendar_event_id" which is the event of the
        next activity. It must evaluate to False if the next activity is not related to an event"""
        def create_event(name, event_date):
            return self.env['calendar.event'].create({
                'name': name,
                'start': datetime.combine(event_date, time(12, 0, 0)),
                'stop': datetime.combine(event_date, time(14, 0, 0)),
            })

        def schedule_meeting_activity(record, date_deadline, calendar_event=False):
            meeting = record.activity_schedule('calendar.calendar_activity_test_default', date_deadline=date_deadline)
            meeting.calendar_event_id = calendar_event
            return meeting

        group_partner_manager = self.env['ir.model.data']._xmlid_to_res_id('base.group_partner_manager')
        self.user_employee.write({
            'tz': self.user_admin.tz,
            'groups_id': [Command.link(group_partner_manager)]
        })
        with self.with_user('employee'):
            test_record = self.env['res.partner'].browse(self.test_record.id)
            self.assertEqual(test_record.activity_ids, self.env['mail.activity'])

            now_utc = datetime.now(pytz.UTC)
            now_user = now_utc.astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
            today_user = now_user.date()

            date1 = today_user + relativedelta(days=1)
            date2 = today_user + relativedelta(days=2)

            ev1 = create_event('ev1', date1)
            ev2 = create_event('ev2', date2)

            act1 = schedule_meeting_activity(test_record, date1)
            schedule_meeting_activity(test_record, date2, ev2)

            self.assertFalse(test_record.activity_calendar_event_id, "The next activity does not have a calendar event")

            act1.calendar_event_id = ev1

            self.assertEqual(test_record.activity_calendar_event_id.name, ev1.name, "This should be the calendar event of the next activity")
