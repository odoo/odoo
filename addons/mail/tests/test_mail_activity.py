# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.mail.models.mail_activity import MailActivity
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form, tagged, HttpCase
from odoo.tools.misc import format_date


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

    def assertActivitiesFromPlan(self, plan, record, expected_deadlines, expected_responsible=None):
        """ Check that the last activities on the record correspond to the one
        that the plan must create (number of activities and activities content).

        We check the created activities values against the template values because
        most of them are just copied when creating activities from templates except
        for deadlines and responsible for which we pass the expected values as parameters.

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset record: record on which the plan has been applied
        :param list<date> expected_deadlines: expected deadlines of the record created activities
        :param <res.user> expected_responsible: expected responsible for the created activities
            if set, otherwise checked against the responsible set on the related templates.
        """
        expected_number_of_activity = len(plan.template_ids)
        activities = self._new_activities.filtered(
            lambda act: act.res_model == record._name and act.res_id == record.id
        )
        self.assertEqual(len(activities), expected_number_of_activity)

        for activity, template, expected_deadline in zip(activities, plan.template_ids, expected_deadlines):
            self.assertEqual(activity.activity_type_id, template.activity_type_id)
            self.assertEqual(activity.date_deadline, expected_deadline)
            self.assertEqual(activity.note, template.note)
            self.assertEqual(activity.summary, template.summary)
            self.assertFalse(activity.automated)
            if expected_responsible:
                self.assertEqual(activity.user_id, expected_responsible)
            else:
                self.assertEqual(activity.user_id, template.responsible_id or self.env.user)

    def assertMessagesFromPlan(self, plan, record, expected_deadlines, expected_responsible=None):
        """ Check that the last posted message on the record correspond to the one
        that the plan must generate (number of activities and activities content).

        :param <mail.activity.plan> plan: activity plan that has been applied on the record
        :param recordset record: record on which the plan has been applied
        :param list<date> expected_deadlines: expected deadlines of the record created activities
        :param <res.user> expected_responsible: expected responsible for the created activities
            if set, otherwise checked against the responsible set on the related templates.
        """
        message = record.message_ids[0]
        self.assertIn(f'The plan "{plan.name}" has been started', message.body)

        for template, expected_deadline in zip(plan.template_ids, expected_deadlines):
            if expected_responsible:
                responsible_id = expected_responsible
            else:
                responsible_id = template.responsible_id or self.env.user

            self.assertIn(template.summary, message.body)
            self.assertIn(f'{template.summary or template.activity_type_id.name}, '
                          f'assigned to {responsible_id.name}, due on the '
                          f'{format_date(self.env, expected_deadline)}', message.body)

    def assertPlanExecution(self, plan, records, expected_deadlines, expected_responsible=None):
        """ Check that the plan has created the right activities and send the
        right message on the records (see assertActivitiesFromPlan and
        assertMessagesFromPlan). """
        for record in records:
            self.assertActivitiesFromPlan(plan, record, expected_deadlines, expected_responsible)
            self.assertMessagesFromPlan(plan, record, expected_deadlines, expected_responsible)

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
            f"/odoo/res.partner/{testuser.partner_id.id}",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )

    def test_mail_activity_date_format(self):
        with freeze_time("2024-1-1 09:00:00 AM"):
            LANG_CODE = "en_US"
            self.env = self.env(context={"lang": LANG_CODE})
            testuser = self.env['res.users'].create({
                "email": "testuser@testuser.com",
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            })
            lang = self.env["res.lang"].search([('code', '=', LANG_CODE)])
            lang.date_format = "%d/%b/%y"
            lang.time_format = "%I:%M:%S %p"

            self.start_tour(
                f"/web#id={testuser.partner_id.id}&model=res.partner",
                "mail_activity_date_format",
                login="admin",
            )
