import csv
import base64
import io
from datetime import date, datetime

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..services.prelog_import.engine import PrelogImportEngine


@tagged('post_install', '-at_install')
class TestPrelogFuzzyMatching(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.week = date(2026, 7, 27)
        cls.program = cls.env['mv.programs'].create({
            'name': 'True Crime Network',
            'clientcode': 'FZY',
        })
        cls.other_program = cls.env['mv.programs'].create({
            'name': 'Other Test Network',
            'clientcode': 'OTH',
        })
        cls.monday = cls.env['mv.days_allowed.tag'].search(
            [('name', '=ilike', 'Mon%')],
            limit=1,
        )
        if not cls.monday:
            cls.monday = cls.env['mv.days_allowed.tag'].create({
                'name': 'Mon',
                'code': 'fuzzy_test_mon',
            })

        cls.deal = cls.env['mv.deal'].create({
            'program': cls.program.id,
            'network_deal_number': 'FZY-100',
            'length': 'v_30',
            'rate': 100.0,
        })
        cls.schedule = cls.env['mv.schedules'].create({
            'deal_parent': cls.deal.id,
            'week': cls.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(cls.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })

        cls.other_deal = cls.env['mv.deal'].create({
            'program': cls.other_program.id,
            'network_deal_number': 'FZY-100',
            'length': 'v_30',
            'rate': 100.0,
        })
        cls.other_schedule = cls.env['mv.schedules'].create({
            'deal_parent': cls.other_deal.id,
            'week': cls.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(cls.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })

    def _create_prelog(self, **overrides):
        values = {
            'import_program': self.program.id,
            'import_week_value': self.week,
            'version': 1,
            'network': self.program.display_name,
            'broadcast_network': 'tCn',
            'network_deal_number': 'FZY-100',
            'airdate': self.week,
            'scheduletime': '09:30:00 AM',
            'schedulelength': '30',
            'rate': 100.0,
            'advertiserproduct': 'Test Advertiser / Product',
            'import_match_status': 'created_without_schedule',
        }
        values.update(overrides)
        return self.env['mv.prelog_data'].create(values)

    def test_search_and_attach_suggested_schedule(self):
        prelog = self._create_prelog()

        result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            1,
        )

        self.assertEqual(result['total'], 1)
        row = result['rows'][0]
        self.assertEqual(row['id'], prelog.id)
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertTrue(row['suggestion_attachable'])
        self.assertFalse(row['reason'])
        self.assertEqual(row['match_quality'], 'exact')

        applied = self.env['mv.prelog_data'].fuzzy_match_apply([{
            'prelog_id': prelog.id,
            'schedule_id': self.schedule.id,
            'source': 'suggested',
        }], self.program.id, self.week.isoformat(), 1)
        self.assertEqual(applied['attached'], 1)
        self.assertEqual(prelog.schedule, self.schedule)
        self.assertEqual(prelog.import_match_status, 'matched')
        self.assertIn('Prelog Fuzzy Matching', prelog.import_match_detail)

        options = self.env['mv.prelog_data'].fuzzy_match_get_options(
            self.program.id,
            self.week.isoformat(),
        )
        self.assertIn(1, options['versions'])

        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].fuzzy_match_apply([{
                'prelog_id': prelog.id,
                'schedule_id': self.schedule.id,
                'source': 'suggested',
            }])

    def test_out_of_rotation_requires_confirmation(self):
        prelog = self._create_prelog(scheduletime='01:00:00 PM')
        result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            1,
        )
        row = result['rows'][0]
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertTrue(row['time_mismatch'])
        self.assertEqual(row['reason'], 'Out of Rotation')

        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].fuzzy_match_apply([{
                'prelog_id': prelog.id,
                'schedule_id': self.schedule.id,
                'source': 'suggested',
            }])

        self.env['mv.prelog_data'].fuzzy_match_apply([{
            'prelog_id': prelog.id,
            'schedule_id': self.schedule.id,
            'source': 'suggested',
            'confirmed_override': True,
        }], self.program.id, self.week.isoformat(), 1)
        self.assertEqual(prelog.schedule, self.schedule)

        exported = self.env['mv.prelog_data'].fuzzy_match_export_csv(
            self.program.id,
            self.week.isoformat(),
            1,
        )
        parsed = list(csv.reader(io.StringIO(exported['content'])))
        self.assertEqual(exported['count'], 1)
        self.assertEqual(parsed[1][-1], 'Out of Rotation')

    def test_network_alias_matches_and_wrong_network_is_rejected(self):
        alias_prelog = self._create_prelog(version=2)
        alias_result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            2,
        )
        self.assertEqual(
            alias_result['rows'][0]['suggested']['id'],
            self.schedule.id,
        )
        self.assertEqual(alias_result['rows'][0]['network'], 'tCn')

        wrong_network = self._create_prelog(
            version=3,
            broadcast_network='Different Network',
        )
        wrong_result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            3,
        )
        self.assertFalse(wrong_result['rows'][0]['suggested'])
        self.assertEqual(
            wrong_result['rows'][0]['reason'],
            'No network match',
        )

        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].fuzzy_match_apply([{
                'prelog_id': wrong_network.id,
                'schedule_id': self.schedule.id,
                'source': 'suggested',
            }], self.program.id, self.week.isoformat(), 3)

        self.assertFalse(alias_prelog.schedule)
        self.assertFalse(wrong_network.schedule)

    def test_generic_program_trusts_selected_import_program(self):
        prelog = self._create_prelog(
            import_program=self.other_program.id,
            network=self.other_program.display_name,
            broadcast_network='Feed Abbreviation',
            version=5,
        )
        result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.other_program.id,
            self.week.isoformat(),
            5,
        )
        self.assertEqual(result['total'], 1)
        self.assertEqual(
            result['rows'][0]['suggested']['id'],
            self.other_schedule.id,
        )
        self.assertFalse(result['rows'][0]['reason'])
        self.assertFalse(prelog.schedule)

    def test_missing_day_or_length_is_not_silently_accepted(self):
        missing_day = self._create_prelog(version=6, airdate=False)
        day_result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            6,
        )
        self.assertFalse(day_result['rows'][0]['suggested'])
        self.assertEqual(day_result['rows'][0]['reason'], 'No day match')

        missing_length = self._create_prelog(
            version=7,
            schedulelength=False,
        )
        length_result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id,
            self.week.isoformat(),
            7,
        )
        self.assertEqual(
            length_result['rows'][0]['suggested']['id'],
            self.schedule.id,
        )
        self.assertTrue(length_result['rows'][0]['length_mismatch'])
        self.assertIn(
            'Length mismatch',
            length_result['rows'][0]['reason'],
        )
        self.assertFalse(missing_day.schedule)
        self.assertFalse(missing_length.schedule)

    def test_apply_rejects_stale_filter_context(self):
        prelog = self._create_prelog(version=4)
        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].fuzzy_match_apply([{
                'prelog_id': prelog.id,
                'schedule_id': self.schedule.id,
                'source': 'suggested',
            }], self.other_program.id, self.week.isoformat(), 4)

        self.assertFalse(prelog.schedule)

    def test_page_requires_fuzzy_matching_operator_access(self):
        user = new_test_user(
            self.env,
            'fuzzy_matching_denied_user',
            groups='base.group_user',
        )
        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].with_user(
                user
            ).fuzzy_match_get_options()

    def test_time_window_handles_midnight(self):
        service = self.env['mv.prelog_data']
        in_window, distance = service._fuzzy_time_window_analysis(
            '01:00 AM',
            '11:00P',
            '02:00A',
            120,
        )
        self.assertTrue(in_window)
        self.assertEqual(distance, 0)

        in_window, distance = service._fuzzy_time_window_analysis(
            '04:30 AM',
            '11:00P',
            '02:00A',
            120,
        )
        self.assertFalse(in_window)
        self.assertEqual(distance, 150)

    def test_prelog_upload_stores_air_time_in_standard_time(self):
        engine = PrelogImportEngine(
            self.env,
            program=self.program,
            upload_file=False,
            upload_filename='',
        )
        base_row = {
            'airdate': self.week,
            'network_deal_number': 'FZY-100',
            'broadcast_network': 'tCn',
            'rate': 100.0,
            'schedulelength': '30',
        }
        military_values = engine.build_row_vals(
            {**base_row, 'scheduletime': '16:46:37'},
            self.week,
            33,
            2,
        )
        standard_values = engine.build_row_vals(
            {**base_row, 'scheduletime': '04:46:37 PM'},
            self.week,
            33,
            3,
        )

        self.assertEqual(military_values['scheduletime'], '4:46:37 PM')
        self.assertEqual(standard_values['scheduletime'], '4:46:37 PM')

    def test_upload_time_window_includes_rotation_boundaries(self):
        engine = PrelogImportEngine(
            self.env,
            program=self.program,
            upload_file=False,
            upload_filename='',
        )

        self.assertTrue(engine._is_valid_schedule_window(
            self.schedule,
            6,
            datetime(2026, 7, 27, 9, 0),
        ))
        self.assertTrue(engine._is_valid_schedule_window(
            self.schedule,
            6,
            datetime(2026, 7, 27, 10, 0),
        ))
        self.assertFalse(engine._is_valid_schedule_window(
            self.schedule,
            6,
            datetime(2026, 7, 27, 8, 59, 59),
        ))
        self.assertFalse(engine._is_valid_schedule_window(
            self.schedule,
            6,
            datetime(2026, 7, 27, 10, 0, 1),
        ))

    def test_upload_time_window_handles_half_hour_overnight_rotation(self):
        overnight_schedule = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id,
            'week': self.week,
            'start_time': 'v_11_00p',
            'end_time': 'v_02_30a',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })
        engine = PrelogImportEngine(
            self.env,
            program=self.program,
            upload_file=False,
            upload_filename='',
        )

        one_am = engine._air_datetime(
            self.week,
            '01:00 AM',
            6,
        )
        end_boundary = engine._air_datetime(
            self.week,
            '02:30 AM',
            6,
        )
        after_end = engine._air_datetime(
            self.week,
            '02:30:01 AM',
            6,
        )

        self.assertEqual(one_am, datetime(2026, 7, 28, 1, 0))
        self.assertTrue(engine._is_valid_schedule_window(
            overnight_schedule,
            6,
            one_am,
        ))
        self.assertTrue(engine._is_valid_schedule_window(
            overnight_schedule,
            6,
            end_boundary,
        ))
        self.assertFalse(engine._is_valid_schedule_window(
            overnight_schedule,
            6,
            after_end,
        ))

    def test_manual_override_must_be_confirmed(self):
        prelog = self._create_prelog(network_deal_number='MISSING')
        with self.assertRaises(UserError):
            self.env['mv.prelog_data'].fuzzy_match_apply([{
                'prelog_id': prelog.id,
                'schedule_ref': self.schedule.name,
                'source': 'manual',
            }])

        self.env['mv.prelog_data'].fuzzy_match_apply([{
            'prelog_id': prelog.id,
            'schedule_ref': str(self.schedule.id),
            'source': 'manual',
            'confirmed_override': True,
        }])
        self.assertEqual(prelog.schedule, self.schedule)

    def test_exception_csv_uses_standard_escaping(self):
        self._create_prelog(
            network_deal_number='MISSING',
            advertiserproduct='=2+2, "Quoted" Product',
        )
        result = self.env['mv.prelog_data'].fuzzy_match_export_csv(
            self.program.id,
            self.week.isoformat(),
            1,
        )
        parsed = list(csv.reader(io.StringIO(result['content'])))

        self.assertEqual(result['count'], 1)
        self.assertEqual(parsed[0][-1], 'Reason')
        self.assertEqual(parsed[1][9], '\'=2+2, "Quoted" Product')
        self.assertEqual(parsed[1][10], 'No schedules found for deal number')

    def test_workbench_tabs_remove_and_unremove_clear_schedule(self):
        matched = self._create_prelog(version=8, schedule=self.schedule.id)
        suggested = self._create_prelog(version=8, advertiserproduct='Suggested')
        no_suggestion = self._create_prelog(
            version=8,
            network_deal_number='NOT-FOUND',
            advertiserproduct='No Suggestion',
        )
        already_removed = self._create_prelog(
            version=8,
            removed=True,
            advertiserproduct='Removed',
        )

        result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 8,
        )
        self.assertEqual(result['counts'], {
            'all': 3,
            'matched': 1,
            'unmatched': 2,
            'suggestions': 1,
            'no_suggestion': 1,
            'removed': 1,
        })
        self.assertNotIn(already_removed.id, [row['id'] for row in result['rows']])

        self.env['mv.prelog_data'].fuzzy_match_set_removed(
            [matched.id], True, self.program.id, self.week.isoformat(), 8,
        )
        self.assertTrue(matched.removed)
        self.assertFalse(matched.schedule)
        self.assertEqual(matched.import_match_status, 'created_without_schedule')

        removed = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 8, 0, 200, 'removed',
        )
        self.assertEqual(removed['total'], 2)
        self.env['mv.prelog_data'].fuzzy_match_set_removed(
            [matched.id], False, self.program.id, self.week.isoformat(), 8,
        )
        self.assertFalse(matched.removed)
        self.assertFalse(matched.schedule)
        refreshed = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 8, 0, 200, 'suggestions',
        )
        self.assertIn(matched.id, [row['id'] for row in refreshed['rows']])
        self.assertIn(suggested.id, [row['id'] for row in refreshed['rows']])
        self.assertFalse(no_suggestion.schedule)

        unmatched = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 8, 0, 200, 'unmatched',
        )
        self.assertEqual(unmatched['total'], 3)
        self.assertEqual(
            {row['id'] for row in unmatched['rows']},
            {matched.id, suggested.id, no_suggestion.id},
        )
        self.assertEqual(
            {row['status'] for row in unmatched['rows']},
            {'suggestion', 'no_suggestion'},
        )

    def test_workbench_filters_are_independently_optional(self):
        other_week = date(2026, 8, 3)
        program_week_v20 = self._create_prelog(version=20)
        program_other_week_v20 = self._create_prelog(
            version=20,
            import_week_value=other_week,
            airdate=other_week,
        )
        other_program_week_v20 = self._create_prelog(
            import_program=self.other_program.id,
            network=self.other_program.display_name,
            broadcast_network='Other Test Network',
            version=20,
        )
        program_week_v21 = self._create_prelog(version=21)

        program_only = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, False, False,
        )
        self.assertEqual(program_only['total'], 3)
        self.assertEqual(
            {row['id'] for row in program_only['rows']},
            {program_week_v20.id, program_other_week_v20.id, program_week_v21.id},
        )

        week_only = self.env['mv.prelog_data'].fuzzy_match_search(
            False, self.week.isoformat(), False,
        )
        self.assertEqual(week_only['total'], 3)
        self.assertEqual(
            {row['id'] for row in week_only['rows']},
            {program_week_v20.id, other_program_week_v20.id, program_week_v21.id},
        )

        version_only = self.env['mv.prelog_data'].fuzzy_match_search(
            False, False, 20,
        )
        self.assertEqual(version_only['total'], 3)
        all_rows = self.env['mv.prelog_data'].fuzzy_match_search(
            False, False, False,
        )
        self.assertGreaterEqual(all_rows['total'], 4)

        options = self.env['mv.prelog_data'].fuzzy_match_get_options(
            self.program.id, False,
        )
        self.assertEqual(options['versions'], [20, 21])

    def test_workbench_single_column_sorting(self):
        rows = [
            {
                'id': 1,
                'status': 'matched',
                'status_label': 'Matched',
                'name': 'Prelog 10',
                'network': 'Zeta Network',
                'air_date': '2026-08-18',
                'air_time': '10:00:00 PM',
                'length': '120',
                'rate': 50.0,
                'deal_number': 'TCN-10',
                'advertiser_product': 'Zebra Product',
                'attached': {'name': 'Schedule 10'},
                'suggested': False,
                'reason': '',
                'time_mismatch': False,
                'length_mismatch': False,
                'ambiguous_count': 0,
            },
            {
                'id': 2,
                'status': 'suggestion',
                'status_label': 'Fuzzy Suggestion',
                'name': 'Prelog 2',
                'network': 'Alpha Network',
                'air_date': '2026-08-18',
                'air_time': '2:00:00 AM',
                'length': '30',
                'rate': 150.0,
                'deal_number': 'TCN-2',
                'advertiser_product': 'Alpha Product',
                'attached': False,
                'suggested': {'name': 'Schedule 2'},
                'reason': 'Out of Rotation',
                'time_mismatch': True,
                'length_mismatch': False,
                'ambiguous_count': 0,
            },
            {
                'id': 3,
                'status': 'matched',
                'status_label': 'Matched',
                'name': 'Prelog 3',
                'network': 'Beta Network',
                'air_date': '2026-08-17',
                'air_time': '11:00:00 AM',
                'length': '60',
                'rate': 100.0,
                'deal_number': 'TCN-3',
                'advertiser_product': 'Beta Product',
                'attached': {'name': 'Schedule 3'},
                'suggested': False,
                'reason': '',
                'time_mismatch': False,
                'length_mismatch': False,
                'ambiguous_count': 0,
            },
        ]
        service = self.env['mv.prelog_data']

        expected_ascending = {
            'status': [2, 3, 1],
            'name': [2, 3, 1],
            'network': [2, 3, 1],
            'air_date': [3, 2, 1],
            'length': [2, 3, 1],
            'rate': [1, 3, 2],
            'deal_number': [2, 3, 1],
            'advertiser_product': [2, 3, 1],
            'schedule': [2, 3, 1],
            'reason': [2, 3, 1],
        }
        for column, expected_ids in expected_ascending.items():
            sorted_rows = service._fuzzy_filter_workbench_rows(
                rows,
                sort_by=column,
                sort_direction='asc',
            )
            self.assertEqual(
                [row['id'] for row in sorted_rows],
                expected_ids,
                'Ascending sort failed for %s' % column,
            )

        descending = service._fuzzy_filter_workbench_rows(
            rows,
            sort_by='air_date',
            sort_direction='desc',
        )
        self.assertEqual([row['id'] for row in descending], [1, 2, 3])

    def test_bulk_all_matching_spans_pages_and_honors_exclusions(self):
        prelogs = self.env['mv.prelog_data'].create([
            {
                'import_program': self.program.id,
                'import_week_value': self.week,
                'version': 30,
                'network': self.program.display_name,
                'broadcast_network': 'tCn',
                'network_deal_number': 'FZY-100',
                'airdate': self.week,
                'scheduletime': '09:30:00 AM',
                'schedulelength': '30',
                'rate': 100.0,
                'advertiserproduct': 'Bulk %s' % index,
                'import_match_status': 'created_without_schedule',
            }
            for index in range(205)
        ])
        page = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 30,
        )
        self.assertEqual(page['total'], 205)
        self.assertEqual(len(page['rows']), 200)

        excluded = prelogs[-1]
        removed = self.env['mv.prelog_data'].fuzzy_workbench_bulk_action(
            'remove',
            {'all_matching': True, 'excluded_ids': [excluded.id]},
            self.program.id,
            self.week.isoformat(),
            30,
        )
        self.assertEqual(removed['updated'], 204)
        self.assertEqual(len(prelogs.filtered('removed')), 204)
        self.assertFalse(excluded.removed)

        deleted = self.env['mv.prelog_data'].fuzzy_workbench_bulk_action(
            'delete',
            {'all_matching': True, 'excluded_ids': []},
            self.program.id,
            self.week.isoformat(),
            30,
            'removed',
        )
        self.assertEqual(deleted['deleted'], 204)
        self.assertEqual(self.env['mv.prelog_data'].search_count([
            ('version', '=', 30),
        ]), 1)

    def test_bulk_attach_suggestions_skips_non_attachable_rows(self):
        attachable = self._create_prelog(version=31)
        no_suggestion = self._create_prelog(
            version=31,
            network_deal_number='NOT-FOUND',
        )
        result = self.env['mv.prelog_data'].fuzzy_workbench_bulk_action(
            'attach',
            {'all_matching': True, 'excluded_ids': []},
            self.program.id,
            self.week.isoformat(),
            31,
            'unmatched',
        )
        self.assertEqual(result['attached'], 1)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(attachable.schedule, self.schedule)
        self.assertFalse(no_suggestion.schedule)

    def test_bulk_fuzzy_attach_requires_confirmation_before_writing(self):
        prelog = self._create_prelog(version=32, scheduletime='11:00:00 AM')
        selection = {'all_matching': False, 'ids': [prelog.id]}
        preview = self.env['mv.prelog_data'].fuzzy_workbench_bulk_action(
            'attach', selection, self.program.id, self.week.isoformat(), 32,
            'suggestions', confirmed_fuzzy=False,
        )
        self.assertTrue(preview['requires_confirmation'])
        self.assertEqual(preview['fuzzy'], 1)
        self.assertFalse(prelog.schedule)

        applied = self.env['mv.prelog_data'].fuzzy_workbench_bulk_action(
            'attach', selection, self.program.id, self.week.isoformat(), 32,
            'suggestions', confirmed_fuzzy=True,
        )
        self.assertEqual(applied['attached'], 1)
        self.assertEqual(prelog.schedule, self.schedule)

    def test_buffer_only_suggestion_is_fuzzy_not_exact(self):
        prelog = self._create_prelog(version=9, scheduletime='11:00:00 AM')
        result = self.env['mv.prelog_data'].fuzzy_match_search(
            self.program.id, self.week.isoformat(), 9, 0, 200, 'suggestions',
        )
        row = result['rows'][0]
        self.assertEqual(row['id'], prelog.id)
        self.assertEqual(row['match_quality'], 'fuzzy')
        self.assertIn('Within fuzzy buffer', row['reason'])

    def test_options_default_to_current_users_latest_completed_upload(self):
        job = self.env['mv.prelog_import_job'].create({
            'state': 'completed',
            'upload_file': base64.b64encode(b'header\nvalue'),
            'upload_filename': 'must-not-be-exposed.csv',
            'file_checksum': 'fuzzy-workbench-options',
            'program_id': self.program.id,
            'import_week': self.week,
            'prelog_version': 10,
            'submitted_by_id': self.env.user.id,
        })
        prelog = self._create_prelog(version=10, import_job=job.id)
        options = self.env['mv.prelog_data'].fuzzy_match_get_options()
        latest = options['latest_upload']
        self.assertEqual(latest['id'], job.id)
        self.assertEqual(latest['program_id'], self.program.id)
        self.assertEqual(latest['version'], 10)
        self.assertEqual(latest['row_count'], 1)
        self.assertNotIn('filename', latest)
        self.assertNotIn('upload_filename', latest)
        self.assertEqual(prelog.import_job, job)
