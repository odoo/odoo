# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.tests import users
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class AppointmentCRMTest(TestCrmCommon):
    @classmethod
    def _create_appointment_type(cls, **kwargs):
        default = {
            "name": "Test Appointment",
            "appointment_duration": 1,
            "appointment_tz": "Europe/Brussels",
            "assign_method": "time_auto_assign",
            "max_schedule_days": 15,
            "min_cancellation_hours": 1,
            "min_schedule_hours": 1,
        }
        return cls.env['appointment.type'].create(dict(default, **kwargs))

    @classmethod
    def setUpClass(cls):
        super(AppointmentCRMTest, cls).setUpClass()
        cls.user_employee = mail_new_test_user(
            cls.env, login='user_employee',
            name='Eglantine Employee', email='eglantine.employee@test.example.com',
            tz='Europe/Brussels', notification_type='inbox',
            company_id=cls.env.ref("base.main_company").id,
            groups='base.group_user',
        )
        cls.appointment_type_nocreate = cls._create_appointment_type(name="No Create")
        cls.appointment_type_create = cls._create_appointment_type(name="Create", lead_create=True)
        cls.categ_id = cls.env.ref('appointment.calendar_event_type_data_online_appointment')

    def _prepare_event_value(self, appointment_type, user, contact, **kwargs):
        partner_ids = (user.partner_id | contact).ids
        default = {
            'name': '%s with %s' % (appointment_type.name, contact.name),
            'start': datetime.now(),
            'start_date': datetime.now(),
            'stop': datetime.now() + timedelta(hours=1),
            'allday': False,
            'duration': appointment_type.appointment_duration,
            'description': "<p>Test</p>",
            'location': appointment_type.location,
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            'categ_ids': [(4, self.categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'user_id': user.id,
        }
        return dict(default, **kwargs)

    def _create_meetings_from_appointment_type(self, appointment_type, user, contact, **kwargs):
        return self.env['calendar.event'].create(self._prepare_event_value(appointment_type, user, contact, **kwargs))

    @users('user_employee')
    def test_create_opportunity(self):
        """ Test the creation of a lead based on the creation of an event
        with appointment type configured to create lead
        """
        event = self._create_meetings_from_appointment_type(
            self.appointment_type_create, self.user_sales_leads, self.contact_1
        )

        self.assertEqual(event.res_model_id, self.env['ir.model']._get('crm.lead'),
            "Event should be linked with the model crm.lead")
        self.assertTrue(event.res_id)
        self.assertTrue(event.opportunity_id)
        lead = event.opportunity_id
        self.assertEqual(lead.user_id, event.user_id)
        self.assertEqual(lead.name, event.name)
        self.assertEqual(lead.description, event.description)
        self.assertEqual(lead.partner_id, self.contact_1)
        self.assertTrue(self.env.ref('appointment_crm.appointment_crm_tag') in lead.tag_ids)
        self.assertTrue(lead.activity_ids[0], "Lead should have a next activity")
        self.assertNotIn(self.env.user.partner_id, lead.message_partner_ids)

        next_activity = lead.activity_ids[0]
        self.assertEqual(next_activity.date_deadline, event.start_date)
        self.assertEqual(next_activity.calendar_event_id, event)

    @users('user_employee')
    def test_create_opportunity_multi(self):
        """ Test the creation of a lead based on the creation of an event
        with appointment type configured to create lead
        """
        events = self.env['calendar.event'].create([
            self._prepare_event_value(
                self.appointment_type_create,
                self.user_sales_leads,
                self.contact_1,
            ),
            self._prepare_event_value(
                self.appointment_type_nocreate,
                self.user_sales_leads,
                self.contact_2,
            ),
            self._prepare_event_value(
                self.appointment_type_create,
                self.user_sales_leads,
                self.contact_1,
                start=datetime.now() + timedelta(hours=1),
                start_date=datetime.now() + timedelta(hours=1),
                stop=datetime.now() + timedelta(hours=2),
        )])
        self.assertTrue(events[0].opportunity_id)
        self.assertFalse(events[1].opportunity_id)
        self.assertTrue(events[2].opportunity_id)
        event1 = events[0]
        next_activity1 = event1.opportunity_id.activity_ids[0]
        self.assertEqual(next_activity1.date_deadline, event1.start_date)
        event2 = events[2]
        next_activity2 = event2.opportunity_id.activity_ids[0]
        self.assertEqual(next_activity2.date_deadline, event2.start_date)

    @users('user_employee')
    def test_create_opportunity_multi_company(self):
        """ Test the creation of a lead when the assignee of the event is in a
        different company than the event creator
        """
        self._activate_multi_company()
        self.user_employee.write({
            'company_ids': [self.company_2.id],
            'company_id': self.company_2,
        })

        event = self.env['calendar.event'].create(self._prepare_event_value(
            self.appointment_type_create,
            self.user_sales_leads,
            self.contact_1,
        ))

        # Sanity checks
        # event organizer -> company_main, event creator -> company_2
        self.assertEqual(event.user_id.company_id, self.company_main)
        self.assertEqual(self.user_employee.company_id, self.company_2)

        # Check if lead is created in company_main
        self.assertTrue(event.opportunity_id)
        lead = event.opportunity_id
        self.assertEqual(lead.user_id, event.user_id)
        self.assertEqual(lead.company_id, self.company_main)

    def test_no_create_lead(self):
        """ Make sure no lead is created for appointment type with create_lead=False """
        event = self._create_meetings_from_appointment_type(
            self.appointment_type_nocreate, self.user_sales_leads, self.contact_1
        )
        self.assertFalse(event.opportunity_id)

    def test_no_partner(self):
        """ Make sure no lead is created if there is no external partner attempting the appointment """
        event = self._create_meetings_from_appointment_type(
            self.appointment_type_create, self.user_sales_leads, self.user_sales_leads.partner_id
        )
        self.assertFalse(event.opportunity_id)

    def test_two_partner(self):
        """ Make sure lead is created if there is two external partner attempting the appointment """
        event_values = self._prepare_event_value(
            self.appointment_type_create,
            self.user_sales_leads,
            self.contact_1,
        )
        event_values['partner_ids'].append((4, self.contact_2.id, False))
        event = self.env['calendar.event'].create(event_values)
        self.assertTrue(event.opportunity_id)

    def test_no_type(self):
        """ Make sure no lead is created, if the appointment type is empty """
        event = self._create_meetings_from_appointment_type(
            self.env['appointment.type'], self.user_sales_leads, self.contact_1
        )
        self.assertFalse(event.opportunity_id)

    def test_tag_deleted(self):
        """ Make sure lead is still created if master data is removed """
        self.env.ref('appointment_crm.appointment_crm_tag').unlink()
        event = self._create_meetings_from_appointment_type(
            self.appointment_type_create, self.user_sales_leads, self.contact_1
        )
        self.assertTrue(event.opportunity_id)
