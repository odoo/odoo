import csv
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
