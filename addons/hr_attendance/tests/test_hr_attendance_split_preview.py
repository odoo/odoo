# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.tests import Form, tagged
from odoo.tests.common import HttpCase, TransactionCase, freeze_time


@tagged('post_install', '-at_install', 'time_rule_pipeline')
class TestAttendanceSplitPreview(TransactionCase):
    """``hr.attendance._get_time_rule_split_preview`` and the form banner built on it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Preview Test Overtime',
            'code': 'OT_PREVIEW_TEST',
        })
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Preview Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [(4, cls.att_type.id)],
        })
        # default company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Preview Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
        })
        cls.env.company.attendance_validation = 'no_validation'

    def _new(self, check_in, check_out, break_duration=0.0):
        return self.env['hr.attendance'].new({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
            'break_duration': break_duration,
            'work_entry_type_id': self.att_type.id,
        })

    def _as_tuples(self, split):
        return [(wet, round(hours, 4)) for wet, hours in split]

    def _employee_attendances(self):
        return self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)], order='check_in')

    def test_preview_overtime_split(self):
        # Monday, 13h for 8h scheduled
        attendance = self._new(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(
            self._as_tuples(attendance._get_time_rule_split_preview()),
            [(self.att_type, 8.0), (self.ot_type, 5.0)],
        )
        self.assertIn('split into 2 attendances', attendance.time_rule_split_preview)
        self.assertFalse(self._employee_attendances(), "the preview must not write anything")

    def test_preview_no_split_within_schedule(self):
        attendance = self._new(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))
        self.assertEqual(self._as_tuples(attendance._get_time_rule_split_preview()), [(self.att_type, 8.0)])
        self.assertFalse(attendance.time_rule_split_preview)

    def test_preview_entirely_overtime_on_day_off(self):
        # Saturday: nothing scheduled, the whole attendance is overtime
        attendance = self._new(datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))
        self.assertEqual(self._as_tuples(attendance._get_time_rule_split_preview()), [(self.ot_type, 3.0)])
        self.assertIn('entirely replaced with', attendance.time_rule_split_preview)

    def test_preview_counts_other_attendances_of_the_day(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 6, 8, 8, 0),
            'check_out': datetime(2026, 6, 8, 12, 0),
        })
        # 4h + 7h = 11h: the last 3h are overtime
        attendance = self._new(datetime(2026, 6, 8, 13, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(
            self._as_tuples(attendance._get_time_rule_split_preview()),
            [(self.att_type, 4.0), (self.ot_type, 3.0)],
        )

    def test_preview_matches_actual_split(self):
        cases = [
            (datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0), 0.0),
            (datetime(2026, 6, 9, 7, 0), datetime(2026, 6, 9, 20, 0), 1.0),
            (datetime(2026, 6, 10, 20, 0), datetime(2026, 6, 11, 9, 0), 0.5),  # crosses midnight
            (datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0), 0.0),  # day off
        ]
        for check_in, check_out, break_duration in cases:
            with self.subTest(check_in=check_in, break_duration=break_duration):
                preview = self._new(check_in, check_out, break_duration)._get_time_rule_split_preview()
                source = self.env['hr.attendance'].create({
                    'employee_id': self.employee.id,
                    'check_in': check_in,
                    'check_out': check_out,
                    'break_duration': break_duration,
                })
                result = (source | source.overtime_attendance_ids).sorted('check_in')
                self.assertEqual(
                    self._as_tuples(preview),
                    [(att.work_entry_type_id, round(att.worked_hours, 4)) for att in result],
                )

    def test_summary_once_split(self):
        """Once split, the dry run has nothing left to do: the summary describes the actual
        parts, the same from the source and from the record created from it."""
        source = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 6, 8, 7, 0),
            'check_out': datetime(2026, 6, 8, 20, 0),
        })
        overtime = source.overtime_attendance_ids
        self.assertTrue(overtime)
        self.assertFalse(source._get_time_rule_split_preview())
        self.assertFalse(overtime._get_time_rule_split_preview())
        summary = source._get_time_rule_split_summary()
        self.assertFalse(summary['pending'])
        self.assertEqual([part['attendance_id'] for part in summary['parts']], [source.id, overtime.id])
        self.assertEqual(overtime._get_time_rule_split_summary(), summary)
        self.assertIn('was split into 2 attendances', source.time_rule_split_preview)

    def test_form_banner_wording(self):
        with Form(self.env['hr.attendance']) as form:
            form.employee_id = self.employee
            form.check_in = datetime(2026, 6, 8, 7, 0)
            form.check_out = datetime(2026, 6, 8, 20, 0)
            self.assertIn('will be split into 2 attendances', form.time_rule_split_preview)
            form.check_out = datetime(2026, 6, 8, 15, 0)
            self.assertFalse(form.time_rule_split_preview)
            form.check_out = datetime(2026, 6, 8, 20, 0)

        self.env.company.attendance_validation = 'manual_validation'
        with Form(self.env['hr.attendance']) as form:
            form.employee_id = self.employee
            form.check_in = datetime(2026, 6, 9, 7, 0)
            form.check_out = datetime(2026, 6, 9, 20, 0)
            self.assertIn('will be split into 2 attendances', form.time_rule_split_preview)
        draft = self._employee_attendances().filtered(lambda a: a.state == 'draft')
        self.assertEqual(len(draft), 1, "the draft attendance must not be split before validation")
        self.assertFalse(draft.overtime_attendance_ids)
        self.assertIn('will be split into 2 attendances', draft.time_rule_split_preview)

    # chatter: hr.attendance._log_time_rule_split

    def _split_messages(self, attendance):
        return attendance.message_ids.filtered(lambda m: 'by the time rules' in (m.body or ''))

    def _create(self, check_in, check_out, **vals):
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
            **vals,
        })

    def test_chatter_logs_split(self):
        source = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        overtime = source.overtime_attendance_ids
        self.assertEqual(len(overtime), 1)
        message = self._split_messages(source)
        self.assertEqual(len(message), 1)
        self.assertIn('into 2 attendances', message.body)
        self.assertIn(self.rule.name, message.body)
        self.assertIn(f'{self.att_type.name}: 08:00', message.body)
        self.assertIn(f'{self.ot_type.name}: 05:00', message.body)
        self.assertIn(f'data-oe-model="hr.attendance" data-oe-id="{overtime.id}"', message.body,
                      "the overtime record must be linked")

    def test_chatter_logs_full_reclassification(self):
        # Saturday: the source itself becomes overtime, no new record
        source = self._create(datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))
        self.assertEqual(source.work_entry_type_id, self.ot_type)
        message = self._split_messages(source)
        self.assertEqual(len(message), 1)
        self.assertIn(f'was entirely replaced with {self.ot_type.name}', message.body)

    def test_chatter_nothing_logged_without_split(self):
        source = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))
        self.assertFalse(self._split_messages(source))

    def test_chatter_logged_on_validation(self):
        self.env.company.attendance_validation = 'manual_validation'
        source = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(source.state, 'draft')
        self.assertFalse(self._split_messages(source), "a draft attendance is not split yet")
        source.action_validate()
        self.assertTrue(source.overtime_attendance_ids)
        self.assertEqual(len(self._split_messages(source)), 1)

    def test_chatter_not_duplicated_on_rerun(self):
        source = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(len(self._split_messages(source)), 1)
        # writing a trigger field re-runs the rules, which leave the split as it is
        source.write({'break_duration': 0.0})
        self.assertEqual(len(self._split_messages(source)), 1)


@tagged('post_install', '-at_install', 'time_rule_pipeline')
class TestAttendanceSplitCheckOut(HttpCase):
    """The split summary of the systray and kiosk check-out routes
    (``hr.attendance._get_time_rule_split_summary``)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Split Check-Out Company'})
        cls.att_type = cls.company.attendance_work_entry_type_id
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Check-Out Test Overtime',
            'code': 'OT_CHECKOUT_TEST',
        })
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Check-Out Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [(4, cls.att_type.id)],
        })
        cls.user = cls.env['res.users'].create({
            'name': 'split_user',
            'login': 'split_user',
            'password': 'split_user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        # company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Split Employee',
            'company_id': cls.company.id,
            'user_id': cls.user.id,
            'tz': 'UTC',
            'barcode': 'SPLIT123',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
        })

    def _check_in(self, check_in):
        # from the employee's company, as the systray and the kiosk: the default time type of an
        # attendance is the current company's, which the rule of this company must match
        self.env['hr.attendance'].with_company(self.company).create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })

    def _systray_check_out(self):
        self.authenticate('split_user', 'split_user')
        return self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})

    def _parts(self, summary):
        return [(part['work_entry_type'], round(part['hours'], 4)) for part in summary['parts']]

    @freeze_time('2026-06-08 20:00:00')  # Monday
    def test_systray_check_out_split(self):
        self._check_in(datetime(2026, 6, 8, 7, 0))
        result = self._systray_check_out()
        summary = result['split_summary']
        self.assertFalse(summary['pending'])
        self.assertEqual(self._parts(summary), [
            (self.att_type.name, 8.0),
            (self.ot_type.name, 5.0),
        ])
        self.assertEqual(result['notification']['type'], 'info')
        self.assertIn('was split into 2 attendances', result['notification']['message'])
        self.assertIn(f'{self.ot_type.name}: 05:00', result['notification']['message'])

    @freeze_time('2026-06-08 20:00:00')
    def test_systray_check_out_split_pending_validation(self):
        self.company.attendance_validation = 'manual_validation'
        self._check_in(datetime(2026, 6, 8, 7, 0))
        result = self._systray_check_out()
        self.assertTrue(result['split_summary']['pending'])
        self.assertIn('will be split into 2 attendances', result['notification']['message'])
        self.assertFalse(self.employee.last_attendance_id.overtime_attendance_ids)

    @freeze_time('2026-06-08 16:00:00')
    def test_systray_check_out_without_split(self):
        self._check_in(datetime(2026, 6, 8, 8, 0))
        result = self._systray_check_out()
        self.assertFalse(result['split_summary'])
        self.assertNotIn('notification', result)

    @freeze_time('2026-06-08 08:00:00')
    def test_systray_check_in_has_no_summary(self):
        result = self._systray_check_out()
        self.assertEqual(self.employee.attendance_state, 'checked_in')
        self.assertNotIn('split_summary', result)

    @freeze_time('2026-06-08 20:00:00')
    def test_kiosk_check_out_split(self):
        self._check_in(datetime(2026, 6, 8, 7, 0))
        result = self.make_jsonrpc_request('/hr_attendance/attendance_barcode_scanned', {
            'token': self.company.attendance_kiosk_key,
            'barcode': 'SPLIT123',
        })
        self.assertEqual(self._parts(result['split_summary']), [
            (self.att_type.name, 8.0),
            (self.ot_type.name, 5.0),
        ])
        self.assertIn('was split into 2 attendances', result['split_summary']['title'])
        # the kiosk shows the split in its greetings, not as a notification
        self.assertNotIn('notification', result)
