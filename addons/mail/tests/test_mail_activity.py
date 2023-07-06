# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.models.mail_activity import MailActivity
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import Form, tagged, HttpCase


class ActivityScheduleCase(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # prepare activities
        cls.activity_type_todo = cls.env.ref('mail.mail_activity_data_todo')
        cls.activity_type_todo.delay_count = 4
        cls.activity_type_call = cls.env.ref('mail.mail_activity_data_call')
        cls.activity_type_call.delay_count = 1

    def reverse_record_set(self, records):
        """ Get an equivalent recordset but with elements in reversed order. """
        return self.env[records._name].browse([record.id for record in reversed(records)])

    def get_last_activities(self, on_record, limit=None):
        """ Get the last activities on the record in id asc order. """
        return self.reverse_record_set(self.env['mail.activity'].search(
            [('res_model', '=', on_record._name), ('res_id', '=', on_record.id)], order='id desc', limit=limit))

    # ------------------------------------------------------------
    # ACTIVITIES MOCK
    # ------------------------------------------------------------

    @contextmanager
    def _mock_activities(self):
        activity_create_origin = MailActivity.create
        self._new_activities = self.env['mail.activity'].sudo()

        def _activity_create(model, *args, **kwargs):
            res = activity_create_origin(model, *args, **kwargs)
            self._new_activities += res.sudo()
            return res

        with patch.object(
                MailActivity, 'create', autospec=True, wraps=MailActivity,
                side_effect=_activity_create
             ) as activity_create_mocked:
            self.activity_create_mocked = activity_create_mocked
            yield

    def assertActivityCreatedOnRecord(self, record, activity_values):
        activity = self._new_activities.filtered(
            lambda act: act.res_model == record._name and act.res_id == record.id
        )
        for fname, fvalue in activity_values.items():
            with self.subTest(fname=fname):
                self.assertEqual(activity[fname], fvalue)

    def assertActivityDoneOnRecord(self, record, activity_type):
        last_message = record.message_ids[0]
        self.assertEqual(last_message.mail_activity_type_id, activity_type)
        self.assertIn(activity_type.name, last_message.body)
        self.assertIn('done', last_message.body)

    def assertActivitiesFromPlan(self, plan, record, force_date_deadline=None, force_responsible_id=None):
        """ Check that the last activities on the record correspond to the one
        that the plan must create (number of activities and activities content).

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset record: record on which the plan has been applied
        :param date force_date_deadline: deadline provided when scheduling the plan
        :param <res.user> force_responsible_id: responsible provided when scheduling the plan
        """
        expected_number_of_activity = len(plan.template_ids)
        activities = self._new_activities.filtered(
            lambda act: act.res_model == record._name and act.res_id == record.id
        )
        self.assertEqual(len(activities), expected_number_of_activity)

        for activity, template in zip(activities, plan.template_ids):
            self.assertEqual(activity.activity_type_id, template.activity_type_id)
            if force_date_deadline:
                self.assertEqual(activity.date_deadline, force_date_deadline)
            else:
                self.assertEqual(activity.date_deadline, fields.Date.today() + timedelta(days=template.activity_type_id.delay_count))
            self.assertEqual(activity.note, template.note)
            self.assertEqual(activity.summary, template.summary)
            if force_responsible_id:
                self.assertEqual(activity.user_id, force_responsible_id)
            else:
                self.assertEqual(activity.user_id, template.responsible_id or self.env.user)

    def assertMessagesFromPlan(self, plan, record, force_date_deadline=None, force_responsible_id=None):
        """ Check that the last posted message on the record correspond to the one
        that the plan must generate (number of activities and activities content).

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset record: record on which the plan has been applied
        :param date force_date_deadline: deadline provided when scheduling the plan
        :param <res.user> force_responsible_id: responsible provided when scheduling the plan
        """
        message = record.message_ids[0]
        self.assertIn(f'The plan "{plan.name}" has been started', message.body)

        for template in plan.template_ids:
            if force_date_deadline:
                date_deadline = force_date_deadline
            else:
                date_deadline = fields.Date.today() + timedelta(days=template.activity_type_id.delay_count)
            if force_responsible_id:
                responsible_id = force_responsible_id
            else:
                responsible_id = template.responsible_id or self.env.user

            self.assertIn(template.summary, message.body)
            self.assertIn(f'{template.summary or template.activity_type_id.name}, '
                          f'assigned to {responsible_id.name}, due on the {date_deadline}', message.body)

    def assertPlanExecution(self, plan, records, force_date_deadline=None, force_responsible_id=None):
        """ Check that the plan has created the right activities and send the
        right message on the records (see assertActivitiesFromPlan and
        assertMessagesFromPlan). """
        for record in records:
            self.assertActivitiesFromPlan(
                plan, record,
                force_date_deadline=force_date_deadline,
                force_responsible_id=force_responsible_id,
            )
            self.assertMessagesFromPlan(
                plan, record,
                force_date_deadline=force_date_deadline,
                force_responsible_id=force_responsible_id,
            )

    def _instantiate_activity_schedule_wizard(self, records, additional_context_value=None):
        """ Get a new Form with context default values referring to the records. """
        return Form(self.env['mail.activity.schedule'].with_context({
            'active_id': records.ids[0],
            'active_ids': records.ids,
            'active_model': records._name,
            **(additional_context_value if additional_context_value else {}),
        }))


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_mail_activity_schedule_from_chatter(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour(
            f"/web#id={testuser.partner_id.id}&model=res.partner",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )
