# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class EventCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(EventCase, cls).setUpClass()

        cls.admin_user = cls.env.ref('base.user_admin')
        cls.admin_user.write({
            'country_id': cls.env.ref('base.be').id,
            'login': 'admin',
            'notification_type': 'inbox',
        })
        cls.company_admin = cls.admin_user.company_id
        # set country in order to format Belgian numbers
        cls.company_admin.write({
            'country_id': cls.env.ref('base.be').id,
        })

        # Test users to use through the various tests
        cls.user_portal = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='patrick.portal@test.example.com',
            groups='base.group_portal',
            login='portal_test',
            name='Patrick Portal',
            notification_type='email',
            tz='Europe/Brussels',
        )
        cls.user_public = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='paulette.public@test.example.com',
            groups='base.group_public',
            login='public_test',
            name='Paulette Public',
            notification_type='email',
            tz='Europe/Brussels',
        )
        cls.user_employee = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='eglantine.employee@test.example.com',
            groups='base.group_user',
            login='user_employee',
            name='Eglantine Employee',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventregistrationdesk = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='ursule.eventregistration@test.example.com',
            login='user_eventregistrationdesk',
            groups='base.group_user,event.group_event_registration_desk',
            name='Ursule EventRegistration',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventuser = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='ursule.eventuser@test.example.com',
            groups='base.group_user,event.group_event_user',
            login='user_eventuser',
            name='Ursule EventUser',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventmanager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='martine.eventmanager@test.example.com',
            groups='base.group_user,event.group_event_manager',
            login='user_eventmanager',
            name='Martine EventManager',
            notification_type='inbox',
            tz='Europe/Brussels',
        )

        cls.event_customer = cls.env['res.partner'].create({
            'name': 'Constantin Customer',
            'email': 'constantin@test.example.com',
            'country_id': cls.env.ref('base.be').id,
            'phone': '0485112233',
            'mobile': False,
        })
        cls.event_customer2 = cls.env['res.partner'].create({
            'name': 'Constantin Customer 2',
            'email': 'constantin2@test.example.com',
            'country_id': cls.env.ref('base.be').id,
            'phone': '0456987654',
            'mobile': '0456654321',
        })
        cls.reference_now = fields.Datetime.from_string('2022-09-05 15:11:34')
        cls.event_type_questions = cls.env['event.type'].create({
            'name': 'Update Type',
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [],
            'event_type_mail_ids': [],
        })

        cls.event_question_1 = cls.env['event.question'].create({
            'title': 'Question1',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': False,
            'answer_ids': [
                (0, 0, {'name': 'Q1-Answer1'}),
                (0, 0, {'name': 'Q1-Answer2'})
            ],
        })
        cls.event_question_2 = cls.env['event.question'].create({
            'title': 'Question2',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': True,
            'answer_ids': [
                (0, 0, {'name': 'Q2-Answer1'}),
                (0, 0, {'name': 'Q2-Answer2'})
            ],
        })
        cls.event_question_3 = cls.env['event.question'].create({
            'title': 'Question3',
            'question_type': 'text_box',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': True,
        })

    @classmethod
    def _create_registrations(cls, event, reg_count):
        # create some registrations
        create_date = fields.Datetime.now()
        registrations = cls.env['event.registration'].create([{
            'create_date': create_date,
            'event_id': event.id,
            'name': f'Test Registration {idx}',
            'email': f'_test_reg_{idx}@example.com',
            'phone': f'04560000{idx}{idx}',
        } for idx in range(0, reg_count)])
        return registrations

    @classmethod
    def _setup_test_reports(cls):
        cls.test_report_view = cls.env["ir.ui.view"].create({
            "arch_db": """
<t t-call="web.html_container">
    <t t-foreach="docs" t-as="registration">
        <t t-call="web.external_layout">
            <div class="page">
                <p>This is a sample of an external report.</p>
            </div>
        </t>
    </t>
</t>""",
            "key": "event_registration_test_report",
            "name": "event_registration_test_report",
            "type": "qweb",
        })
        cls.env["ir.model.data"].create({
            "model": "ir.ui.view",
            "module": "event",
            "name": "event_registration_test_report",
            "res_id": cls.test_report_view.id,
        })

        cls.test_report_action = cls.env['ir.actions.report'].create({
            'name': 'Test Report on event.registration',
            'model': 'event.registration',
            'print_report_name': "f'TestReport for {object.name}'",
            'report_type': 'qweb-pdf',
            'report_name': 'event.event_registration_test_report',
        })

        cls.template_subscription = cls.env['mail.template'].create({
            "body_html": """<div>Hello your registration to <t t-out="object.event_id.name"/> is confirmed.</div>""",
            "email_from": "{{ (object.event_id.organizer_id.email_formatted or object.event_id.user_id.email_formatted or '') }}",
            "email_to": """{{ (object.email and '"%s" <%s>' % (object.name, object.email)) or object.partner_id.email_formatted or '' }}""",
            "lang": "{{ object.event_id.lang or object.partner_id.lang }}",
            "model_id": cls.env['ir.model']._get_id("event.registration"),
            "name": "Event: Registration Confirmation TEST",
            "subject": "Confirmation for {{ object.event_id.name }}",
            "report_template_ids": [(4, cls.test_report_action.id)],
        })
        cls.template_reminder = cls.env['mail.template'].create({
            "body_html": """<div>Hello this is a reminder for your registration to  <t t-out="object.event_id.name"/>.</div>""",
            "email_from": "{{ (object.event_id.organizer_id.email_formatted or object.event_id.user_id.email_formatted or '') }}",
            "email_to": """{{ (object.email and '"%s" <%s>' % (object.name, object.email)) or object.partner_id.email_formatted or '' }}""",
            "lang": "{{ object.event_id.lang or object.partner_id.lang }}",
            "model_id": cls.env['ir.model']._get_id("event.registration"),
            "name": "Event: Registration Reminder TEST",
            "subject": "Reminder for {{ object.event_id.name }}: {{ object.event_date_range }}",
            "report_template_ids": [(4, cls.test_report_action.id)],
        })

    def assertSchedulerCronTriggers(self, capture, call_at_list):
        self.assertEqual(len(capture.records), len(call_at_list))
        for record, call_at in zip(capture.records, call_at_list):
            self.assertEqual(record.call_at, call_at.replace(microsecond=0))
            self.assertEqual(record.cron_id, self.env.ref('event.event_mail_scheduler'))
