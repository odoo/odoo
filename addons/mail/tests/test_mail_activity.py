# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
import freezegun
from itertools import product

from odoo import tests
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_chatter_activity_tour(self):
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


@tests.tagged('mail_activity')
class TestMailActivity(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def date_delta_now(days):
            return datetime.date.today() + relativedelta(days=days)

        cls.todo_activity_type = cls.env['mail.activity.type'].create({
            'name': 'To do',
            'res_model': False,
        })
        cls.call_activity_type = cls.env['mail.activity.type'].create({
            'name': 'Call',
            'res_model': False,
        })
        cls.res_model_id = cls.env['ir.model']._get_id('res.partner')
        cls.responsible1, cls.responsible2, cls.responsible3 = cls.env['res.users'].create([
            {
                'login': f'responsible{idx}@odoo.com',
                'email': f'responsible{idx}@odoo.com',
                'name': f'responsible{idx}',
            }
            for idx in range(3)
        ])
        cls.record1 = cls.env['res.partner'].create({'name': 'customer 1'})
        cls.record2 = cls.env['res.partner'].create({'name': 'customer 2'})
        cls.record_with_todo_done = cls.env['res.partner'].create({'name': 'customer 3'})
        cls.record_with_call_done = cls.env['res.partner'].create({'name': 'customer 4'})
        cls.record_no_activity = cls.env['res.partner'].create({'name': 'customer 5'})
        cls.col_record, cls.col_summary, cls.col_deadline, cls.col_date_done, cls.col_state, cls.col_responsible, \
            cls.col_activity, cls.col_id = range(8)
        cls.record1_todo_overdue_line = 2
        cls.record1_call_planned_line = 2
        cls.record2_todo_planned_line = 5
        cls.record2_call_closest_done_line = 4
        cls.todo_activity_def = [
            [cls.record1, 'Prepare quotation', date_delta_now(-7), date_delta_now(-6), 'done', cls.responsible1],
            [cls.record1, 'Send quotation', date_delta_now(-3), date_delta_now(-3), 'done', cls.responsible2],
            [cls.record1, 'Discuss project', date_delta_now(-1), False, 'overdue', cls.responsible3],
            [cls.record1, 'Send product', date_delta_now(0), False, 'today', cls.responsible1],
            [cls.record1, 'Get feedback', date_delta_now(7), False, 'planned', cls.responsible2],
            [cls.record2, 'Meet lead', date_delta_now(3), False, 'planned', cls.responsible3],
            [cls.record_with_todo_done, 'Meet', date_delta_now(-15), date_delta_now(-15), 'done', cls.responsible1],
        ]
        cls.call_activity_def = [
            [cls.record1, 'Call lead', date_delta_now(-7), date_delta_now(-7), 'done', cls.responsible1],
            [cls.record1, 'Get requirement', date_delta_now(-3), date_delta_now(-3), 'done', cls.responsible2],
            [cls.record1, 'Satisfaction survey', date_delta_now(15), False, 'planned', cls.responsible3],
            [cls.record2, 'Call lead', date_delta_now(-3), date_delta_now(-4), 'done', cls.responsible1],
            [cls.record2, 'Get requirement', date_delta_now(-1), date_delta_now(-1), 'done', cls.responsible2],
            [cls.record_with_call_done, 'Call', date_delta_now(-15), date_delta_now(-16), 'done', cls.responsible2],
        ]
        with freezegun.freeze_time(date_delta_now(-14)):
            for activity_type, definitions in (
                    (cls.todo_activity_type, cls.todo_activity_def),
                    (cls.call_activity_type, cls.call_activity_def),
            ):
                for definition in definitions:  # Batch create cause an error
                    activity = cls.env['mail.activity'].create({
                        'activity_type_id': activity_type.id,
                        'date_deadline': definition[cls.col_deadline],
                        'res_id': definition[cls.col_record].id,
                        'res_model_id': cls.res_model_id,
                        'summary': definition[cls.col_summary],
                        'user_id': definition[cls.col_responsible].id,
                    })
                    date_done = definition[cls.col_date_done]
                    definition.append(activity)
                    if date_done:
                        with freezegun.freeze_time(date_done):
                            activity.with_user(definition[cls.col_responsible]).action_done()
                        definition.append(
                            cls.env['mail.message'].search(
                                [('mail_activity_type_id', '=', activity_type.id)], limit=1, order='id desc').id
                        )
                    else:
                        definition.append(activity.id)

    def _get_ids(self, activities_def, record):
        return list(map(
            lambda a: a[self.col_id],
            sorted(filter(lambda a: a[self.col_record] == record and a[self.col_state] != 'done', activities_def),
                   key=lambda a: a[self.col_deadline])
        ))

    def _get_completed_ids(self, activities_def, record):
        return list(map(
            lambda a: a[self.col_id],
            sorted(filter(lambda a: a[self.col_record] == record and a[self.col_state] == 'done', activities_def),
                   key=lambda a: a[self.col_date_done], reverse=True)
        ))

    def test_initial_values(self):
        for activity_def in (self.todo_activity_def, self.todo_activity_def):
            for definition in activity_def:
                self.assertTrue(definition[self.col_id])

    def test_get_activity_data(self):
        """ Check get_activity_data values. """
        for todo_display_done, call_display_done in product((False, True), (False, True)):
            self.todo_activity_type.display_done = todo_display_done
            self.call_activity_type.display_done = call_display_done
            activity_data = self.env['mail.activity'].get_activity_data('res.partner', None)
            grouped_activities = activity_data['grouped_activities']
            record1_todo = grouped_activities[self.record1.id][self.todo_activity_type.id]
            record1_call = grouped_activities[self.record1.id][self.call_activity_type.id]
            record2_todo = grouped_activities[self.record2.id][self.todo_activity_type.id]

            self.assertEqual(activity_data['activity_res_ids'],
                             [self.record1.id, self.record2.id,
                              # record_with_todo_done is more recent than record_with_call_done -> order is important
                              *([self.record_with_todo_done.id] if todo_display_done else []),
                              *([self.record_with_call_done.id] if call_display_done else [])])
            self.assertEqual(record1_todo['count_by_state'], {
                'overdue': 1,
                'today': 1,
                'planned': 1,
                **({'done': 2} if todo_display_done else {}),
            })
            self.assertEqual(record1_todo['ids'], self._get_ids(self.todo_activity_def, self.record1))
            self.assertEqual(record1_todo['completed_activity_ids'],
                             self._get_completed_ids(self.todo_activity_def, self.record1) if todo_display_done else [])
            self.assertEqual(record1_todo['state'], 'overdue')
            self.assertEqual(record1_todo['user_ids_ordered_by_deadline'],
                             [self.responsible3.id, self.responsible1.id, self.responsible2.id])
            self.assertEqual(record1_todo['o_closest_date'],
                             self.todo_activity_def[self.record1_todo_overdue_line][self.col_deadline])
            self.assertEqual(record1_call['count_by_state'], {
                'planned': 1,
                **({'done': 2} if call_display_done else {}),
            })
            self.assertEqual(record1_call['ids'], self._get_ids(self.call_activity_def, self.record1))
            self.assertEqual(record1_call['completed_activity_ids'],
                             self._get_completed_ids(self.call_activity_def, self.record1) if call_display_done else [])
            self.assertEqual(record1_call['state'], 'planned')
            self.assertEqual(record1_call['user_ids_ordered_by_deadline'], [self.responsible3.id])
            self.assertEqual(record1_call['o_closest_date'],
                             self.call_activity_def[self.record1_call_planned_line][self.col_deadline])
            self.assertEqual(record2_todo['count_by_state'], {
                'planned': 1,
            })
            self.assertEqual(record2_todo['ids'], self._get_ids(self.todo_activity_def, self.record2))
            self.assertEqual(record2_todo['completed_activity_ids'],
                             self._get_completed_ids(self.todo_activity_def, self.record2) if todo_display_done else [])
            self.assertEqual(record2_todo['state'], 'planned')
            self.assertEqual(record2_todo['user_ids_ordered_by_deadline'], [self.responsible3.id])
            self.assertEqual(record2_todo['o_closest_date'],
                             self.todo_activity_def[self.record2_todo_planned_line][self.col_deadline])
            if call_display_done:
                record2_call = grouped_activities[self.record2.id][self.call_activity_type.id]
                self.assertEqual(record2_call['count_by_state'], {
                    'done': 2,
                })
                self.assertEqual(record2_call['ids'], self._get_ids(self.call_activity_def, self.record2))
                self.assertEqual(record2_call['completed_activity_ids'],
                                 self._get_completed_ids(
                                     self.call_activity_def, self.record2) if call_display_done else [])
                self.assertEqual(record2_call['state'], 'done')
                self.assertEqual(record2_call['user_ids_ordered_by_deadline'], [])
                self.assertEqual(record2_call['o_closest_date'],
                                 self.call_activity_def[self.record2_call_closest_done_line][self.col_date_done])
            else:
                self.assertTrue(self.call_activity_type.id not in grouped_activities[self.record2.id])

    def test_get_activity_data_filters_and_search_fields(self):
        """ Test activity filters """
        self.todo_activity_type.display_done = True
        self.call_activity_type.display_done = True

        for responsible, assertions in (
                (self.responsible1, (
                        (self.record1, self.todo_activity_type, {'today': 1, 'done': 1}),
                        (self.record1, self.call_activity_type, {'done': 1}),
                        (self.record2, self.todo_activity_type, False),
                        (self.record2, self.call_activity_type, {'done': 1})),
                 ),
                (self.responsible2, (
                        (self.record1, self.todo_activity_type, {'planned': 1, 'done': 1}),
                        (self.record1, self.call_activity_type, {'done': 1}),
                        (self.record2, self.todo_activity_type, False),
                        (self.record2, self.call_activity_type, {'done': 1})),
                 ),
                (self.responsible3, (
                        (self.record1, self.todo_activity_type, {'overdue': 1}),
                        (self.record1, self.call_activity_type, {'planned': 1}),
                        (self.record2, self.todo_activity_type, {'planned': 1}),
                        (self.record2, self.call_activity_type, False)),
                 ),
        ):
            # Test with only "activities_my" filter
            activity_data = self.env['mail.activity'].with_user(responsible).get_activity_data(
                'res.partner', domain=[('has_visible_activities', '=', True)], activity_filters=('activities_my',))
            grouped_activities = activity_data['grouped_activities']
            for record, activity_type, expected in assertions:
                self.assertEqual(
                    grouped_activities.get(record.id, {}).get(activity_type.id, {}).get('count_by_state', False),
                    expected
                )
            # Test with one and 2 combined state filter and state search field on top of the "activities_my" filter
            cases = [(state_filter, activity_search_field_state)
                     for state_filter in ({'overdue'}, {'planned', 'today'})
                     for activity_search_field_state in [None, *state_filter]]
            for state_filter, activity_search_field_state in cases:
                activity_filters = ['activities_my', *[f'activities_state_{state}' for state in state_filter]]
                activity_search_fields = [
                    ('activity_state', activity_search_field_state)] if activity_search_field_state else None
                activity_data = self.env['mail.activity'].with_user(responsible).get_activity_data(
                    'res.partner',
                    domain=[('has_visible_activities', '=', True)],
                    activity_filters=activity_filters, activity_search_fields=activity_search_fields)
                grouped_activities = activity_data['grouped_activities']
                for record, activity_type, expected_without_state_filter in assertions:
                    expected = {state: state_count
                                for state, state_count in expected_without_state_filter.items()
                                if state in state_filter and (activity_search_field_state is None or
                                                              state == activity_search_field_state)
                                } or False if expected_without_state_filter else False
                    self.assertEqual(
                        grouped_activities.get(record.id, {}).get(activity_type.id, {}).get('count_by_state', False),
                        expected,
                        f'{expected} for activity_filters={activity_filters}, '
                        f'activity_search_fields={activity_search_fields}'
                    )
        # Test state filters and search state field without "activities_my" filter
        for record, activity_type, expected_without_state_filter in (
                (self.record1, self.todo_activity_type, {'done': 2, 'overdue': 1, 'planned': 1, 'today': 1}),
                (self.record1, self.call_activity_type, {'done': 2, 'planned': 1}),
                (self.record2, self.todo_activity_type, {'planned': 1}),
                (self.record2, self.call_activity_type, {'done': 2}),
            ):
            # Test with one and 2 combined state filter and state search field on top of the "activities_my" filter
            cases = [(state_filter, activity_search_field_state)
                     for state_filter in ({'overdue'}, {'planned', 'today'})
                     for activity_search_field_state in [None, *state_filter]]
            for state_filter, activity_search_field_state in cases:
                activity_filters = [f'activities_state_{state}' for state in state_filter]
                activity_search_fields = [
                    ('activity_state', activity_search_field_state)] if activity_search_field_state else None
                activity_data = self.env['mail.activity'].with_user(responsible).get_activity_data(
                    'res.partner',
                    domain=[('has_visible_activities', '=', True)],
                    activity_filters=activity_filters, activity_search_fields=activity_search_fields)
                grouped_activities = activity_data['grouped_activities']
                expected = {state: state_count
                            for state, state_count in expected_without_state_filter.items()
                            if state in state_filter and (activity_search_field_state is None or
                                                          state == activity_search_field_state)
                            } or False if expected_without_state_filter else False
                self.assertEqual(
                    grouped_activities.get(record.id, {}).get(activity_type.id, {}).get('count_by_state', False),
                    expected
                )
        # Test activity_user_id
        for responsible, assertions in (
                (self.responsible1, (
                        (self.record1, self.todo_activity_type, {'done': 1, 'today': 1}),
                        (self.record2, self.todo_activity_type, False),
                )),
                (self.responsible2, (
                        (self.record1, self.call_activity_type, {'done': 1}),
                        (self.record2, self.call_activity_type, {'done': 1}),
                ))
                ,
                (self.responsible3, (
                        (self.record1, self.todo_activity_type, {'overdue': 1}),
                        (self.record2, self.todo_activity_type, {'planned': 1}),
                )),
        ):
            activity_data = self.env['mail.activity'].get_activity_data(
                'res.partner',
                domain=[('has_visible_activities', '=', True)],
                activity_filters=None, activity_search_fields=[('activity_user_id', responsible.name)])
            grouped_activities = activity_data['grouped_activities']
            for record, activity_type, expected_count_by_state in assertions:
                self.assertEqual(
                    grouped_activities.get(record.id, {}).get(activity_type.id, {}).get('count_by_state', False),
                    expected_count_by_state
                )
