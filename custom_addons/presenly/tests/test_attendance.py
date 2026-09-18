from datetime import datetime

import pytz
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestPresenlyAttendance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.school_one_address = cls.env['res.partner'].create({
            'name': 'School One Address',
            'company_id': cls.company.id,
            'partner_latitude': -6.200000,
            'partner_longitude': 106.816666,
        })
        cls.school_two_address = cls.env['res.partner'].create({
            'name': 'School Two Address',
            'company_id': cls.company.id,
            'partner_latitude': -6.210000,
            'partner_longitude': 106.826666,
        })
        cls.school_one = cls.env['hr.work.location'].create({
            'name': 'School One',
            'company_id': cls.company.id,
            'address_id': cls.school_one_address.id,
        })
        cls.school_two = cls.env['hr.work.location'].create({
            'name': 'School Two',
            'company_id': cls.company.id,
            'address_id': cls.school_two_address.id,
        })
        cls.working_hours = cls.env['resource.calendar'].create({
            'name': 'Teacher Split-School Working Hours',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'attendance_ids': [
                Command.create({
                    'name': 'Monday Morning',
                    'dayofweek': '0',
                    'day_period': 'morning',
                    'hour_from': 7.0,
                    'hour_to': 11.0,
                }),
                Command.create({
                    'name': 'Monday Afternoon',
                    'dayofweek': '0',
                    'day_period': 'afternoon',
                    'hour_from': 13.0,
                    'hour_to': 16.0,
                }),
                Command.create({
                    'name': 'Tuesday Morning',
                    'dayofweek': '1',
                    'day_period': 'morning',
                    'hour_from': 8.0,
                    'hour_to': 12.0,
                }),
            ],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Teacher at Two Schools',
            'company_id': cls.company.id,
            'work_location_id': cls.school_one.id,
            'resource_calendar_id': cls.working_hours.id,
            'tz': 'UTC',
        })
        cls.monday_morning = cls.env['presenly.work.location.schedule'].create({
            'employee_id': cls.employee.id,
            'work_location_id': cls.school_one.id,
            'schedule_type': 'weekly',
            'weekday': '0',
            'hour_from': 7.0,
            'hour_to': 11.0,
            'check_in_tolerance_minutes': 0,
        })
        cls.monday_afternoon = cls.env['presenly.work.location.schedule'].create({
            'employee_id': cls.employee.id,
            'work_location_id': cls.school_two.id,
            'schedule_type': 'weekly',
            'weekday': '0',
            'hour_from': 13.0,
            'hour_to': 16.0,
            'check_in_tolerance_minutes': 0,
        })

    def _utc_for_local(self, year, month, day, hour, minute=0):
        timezone = pytz.timezone(self.employee._get_tz())
        local_value = timezone.localize(datetime(year, month, day, hour, minute))
        return local_value.astimezone(pytz.UTC).replace(tzinfo=None)

    def test_default_radius_and_geofence(self):
        self.assertEqual(self.school_one.presenly_radius_meters, 150.0)
        self.assertTrue(
            self.school_one.is_coordinate_allowed(-6.2005, 106.816666, 10)
        )
        self.assertFalse(
            self.school_one.is_coordinate_allowed(-6.205, 106.816666, 10)
        )

    def test_gps_accuracy_limit(self):
        self.assertFalse(
            self.school_one.is_coordinate_allowed(-6.2, 106.816666, 101)
        )

    def test_invalid_coordinates(self):
        with self.assertRaises(ValidationError):
            self.school_one.is_coordinate_allowed(91, 106.816666, 10)

    def test_two_schools_in_one_day_are_resolved_by_time(self):
        morning_locations, morning_slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 8),
        )
        afternoon_locations, afternoon_slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 14),
        )
        self.assertEqual(morning_locations, self.school_one)
        self.assertEqual(morning_slots, self.monday_morning)
        self.assertEqual(afternoon_locations, self.school_two)
        self.assertEqual(afternoon_slots, self.monday_afternoon)

    def test_no_native_fallback_between_scheduled_slots(self):
        locations, slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 12),
        )
        self.assertFalse(locations)
        self.assertFalse(slots)

    def test_specific_date_replaces_weekly_schedule(self):
        exception = self.env['presenly.work.location.schedule'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.school_two.id,
            'schedule_type': 'date',
            'schedule_date': '2030-01-07',
            'hour_from': 9.0,
            'hour_to': 10.0,
            'check_in_tolerance_minutes': 0,
        })
        locations, slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 9, 30),
        )
        self.assertEqual(locations, self.school_two)
        self.assertEqual(slots, exception)
        locations, slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 8),
        )
        self.assertFalse(locations)
        self.assertFalse(slots)

    def test_overlapping_weekly_slots_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['presenly.work.location.schedule'].create({
                'employee_id': self.employee.id,
                'work_location_id': self.school_two.id,
                'schedule_type': 'weekly',
                'weekday': '0',
                'hour_from': 10.0,
                'hour_to': 12.0,
            })

    def test_location_slot_outside_working_hours_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, 'Working Hours'):
            self.env['presenly.work.location.schedule'].create({
                'employee_id': self.employee.id,
                'work_location_id': self.school_one.id,
                'schedule_type': 'weekly',
                'weekday': '0',
                'hour_from': 11.0,
                'hour_to': 12.0,
            })

    def test_calendar_change_marks_conflict_and_resolver_ignores_slot(self):
        self.working_hours.attendance_ids.filtered(
            lambda attendance: attendance.dayofweek == '0'
            and attendance.hour_from == 7.0
        ).write({'hour_from': 8.0})
        self.assertEqual(self.monday_morning.calendar_sync_state, 'outside')
        self.assertEqual(self.employee.presenly_schedule_health, 'conflict')
        locations, slots = self.employee._presenly_locations_at(
            self._utc_for_local(2030, 1, 7, 7, 30),
        )
        self.assertFalse(locations)
        self.assertFalse(slots)
        self.monday_morning.active = False
        self.assertFalse(self.monday_morning.active)

    def test_generator_fills_working_hours_gaps(self):
        self.monday_morning.unlink()
        self.monday_afternoon.unlink()
        wizard = self.env['presenly.schedule.generate.wizard'].create({
            'employee_id': self.employee.id,
            'default_work_location_id': self.school_one.id,
            'generation_mode': 'gaps',
            'check_in_tolerance_minutes': 15,
        })
        wizard._prepare_lines()
        self.assertEqual(len(wizard.line_ids), 3)
        monday_lines = wizard.line_ids.filtered(lambda line: line.weekday == '0')
        self.assertEqual(len(monday_lines), 2)
        afternoon = monday_lines.filtered(lambda line: line.hour_from == 13.0)
        afternoon.work_location_id = self.school_two
        wizard.action_generate()
        generated = self.employee.presenly_schedule_ids.filtered(
            lambda slot: slot.schedule_type == 'weekly'
        )
        self.assertEqual(len(generated), 3)
        self.assertEqual(
            generated.filtered(lambda slot: slot.hour_from == 13.0).work_location_id,
            self.school_two,
        )
        self.assertEqual(self.employee.presenly_schedule_health, 'synced')
        self.assertEqual(self.employee.presenly_schedule_gap_count, 0)

    def test_generator_can_split_one_work_period_between_locations(self):
        self.monday_morning.unlink()
        self.monday_afternoon.unlink()
        wizard = self.env['presenly.schedule.generate.wizard'].create({
            'employee_id': self.employee.id,
            'default_work_location_id': self.school_one.id,
            'generation_mode': 'gaps',
        })
        wizard._prepare_lines()
        morning = wizard.line_ids.filtered(
            lambda line: line.weekday == '0' and line.hour_from == 7.0
        )
        morning.hour_to = 9.0
        self.env['presenly.schedule.generate.wizard.line'].create({
            'wizard_id': wizard.id,
            'weekday': '0',
            'hour_from': 9.0,
            'hour_to': 11.0,
            'work_location_id': self.school_two.id,
        })
        wizard.action_generate()
        monday = self.employee.presenly_schedule_ids.filtered(
            lambda slot: slot.schedule_type == 'weekly' and slot.weekday == '0'
        )
        self.assertEqual(len(monday), 3)
        self.assertEqual(
            monday.filtered(lambda slot: slot.hour_from == 9.0).work_location_id,
            self.school_two,
        )

    def test_two_week_calendar_requires_and_resolves_week_type(self):
        two_week_calendar = self.env['resource.calendar'].create({
            'name': 'Alternating School Hours',
            'company_id': self.company.id,
            'tz': 'UTC',
            'two_weeks_calendar': True,
            'attendance_ids': [
                Command.create({
                    'name': 'Week 1 Wednesday',
                    'dayofweek': '2',
                    'week_type': '0',
                    'day_period': 'morning',
                    'hour_from': 8.0,
                    'hour_to': 12.0,
                }),
                Command.create({
                    'name': 'Week 2 Wednesday',
                    'dayofweek': '2',
                    'week_type': '1',
                    'day_period': 'morning',
                    'hour_from': 9.0,
                    'hour_to': 13.0,
                }),
            ],
        })
        alternating_employee = self.env['hr.employee'].create({
            'name': 'Alternating Teacher',
            'company_id': self.company.id,
            'work_location_id': self.school_one.id,
            'resource_calendar_id': two_week_calendar.id,
            'tz': 'UTC',
        })
        missing_week_slot = self.env['presenly.work.location.schedule'].new({
            'employee_id': alternating_employee.id,
            'work_location_id': self.school_one.id,
            'schedule_type': 'weekly',
            'weekday': '2',
            'hour_from': 8.0,
            'hour_to': 12.0,
        })
        state, message = missing_week_slot._presenly_calendar_sync_values()
        self.assertEqual(state, 'outside')
        self.assertIn('Week 1 or Week 2', message)
        slot = self.env['presenly.work.location.schedule'].create({
            'employee_id': alternating_employee.id,
            'work_location_id': self.school_one.id,
            'schedule_type': 'weekly',
            'weekday': '2',
            'week_type': '0',
            'hour_from': 8.0,
            'hour_to': 12.0,
            'check_in_tolerance_minutes': 0,
        })
        self.assertEqual(slot.calendar_sync_state, 'valid')

    def test_cross_company_schedule_is_rejected(self):
        other_company = self.env['res.company'].create({
            'name': 'Other School Company',
        })
        other_address = self.env['res.partner'].create({
            'name': 'Other Company Address',
            'company_id': other_company.id,
            'partner_latitude': -6.22,
            'partner_longitude': 106.83,
        })
        other_location = self.env['hr.work.location'].create({
            'name': 'Other Company School',
            'company_id': other_company.id,
            'address_id': other_address.id,
        })
        with self.assertRaises(ValidationError):
            self.env['presenly.work.location.schedule'].with_context(
                allowed_company_ids=(self.company | other_company).ids,
                check_company=False,
            ).create({
                'employee_id': self.employee.id,
                'work_location_id': other_location.id,
                'schedule_type': 'weekly',
                'weekday': '1',
                'hour_from': 8.0,
                'hour_to': 12.0,
            })


class TestPresenlyAttendanceFormSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee_user = new_test_user(
            cls.env,
            login='presenly_attendance_form_employee',
            groups=(
                'base.group_user,presenly.group_presenly_employee,'
                'hr_attendance.group_hr_attendance_user'
            ),
        )
        cls.hr_user = new_test_user(
            cls.env,
            login='presenly_attendance_form_hr',
            groups='base.group_user,presenly.group_presenly_hr',
        )
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Attendance Form Employee',
            'company_id': cls.company.id,
            'user_id': cls.employee_user.id,
            'attendance_manager_id': cls.hr_user.id,
        })
        cls.other_employee = cls.env['hr.employee'].create({
            'name': 'Attendance Form Other Employee',
            'company_id': cls.company.id,
            'attendance_manager_id': cls.hr_user.id,
        })
        cls.attendance = cls.env['hr.attendance']._presenly_mobile_create({
            'employee_id': cls.employee.id,
            'check_in': '2030-01-02 08:00:00',
            'check_out': '2030-01-02 16:00:00',
            'presenly_source': 'mobile',
        })

    def test_employee_cannot_reassign_attendance_despite_native_group(self):
        attendance = self.attendance.with_user(self.employee_user)
        self.assertFalse(attendance._presenly_user_can_change_employee())
        attendance.invalidate_recordset(['is_manager'])
        self.assertFalse(attendance.is_manager)
        with self.assertRaisesRegex(ValidationError, 'history is read-only'):
            attendance.write({'employee_id': self.other_employee.id})
        self.assertEqual(self.attendance.employee_id, self.employee)

    def test_hr_cannot_change_attendance_history(self):
        attendance = self.attendance.with_user(self.hr_user)
        self.assertTrue(attendance._presenly_user_can_change_employee())
        with self.assertRaisesRegex(ValidationError, 'history is read-only'):
            attendance.write({'employee_id': self.other_employee.id})
        self.assertEqual(self.attendance.employee_id, self.employee)

    def test_manual_create_delete_and_native_toggle_are_blocked(self):
        with self.assertRaisesRegex(ValidationError, 'Presenly check-in'):
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2030-01-03 08:00:00',
            })
        # Any user without the Presenly HR/Administrator role cannot delete.
        with self.assertRaisesRegex(ValidationError, 'Administrator or HR Officer'):
            self.attendance.with_user(self.employee_user).unlink()
        with self.assertRaisesRegex(ValidationError, 'Presenly mobile application'):
            self.employee._attendance_action_change({'mode': 'systray'})
        with self.assertRaises(AccessError):
            from odoo.service.model import get_public_method
            get_public_method(self.env['hr.attendance'], '_presenly_mobile_create')

    def test_admin_can_delete_and_purges_children(self):
        event = self.env['presenly.attendance.event'].create({
            'employee_id': self.employee.id,
            'attendance_id': self.attendance.id,
            'event_type': 'check_in',
            'source': 'mobile',
            'validation_status': 'success',
        })
        attendance_id = self.attendance.id
        event_id = event.id
        self.attendance.unlink()
        self.assertFalse(self.attendance.exists())
        self.assertFalse(event.exists())
        logs = self.env['presenly.deletion.log'].search([
            ('res_model', '=', 'hr.attendance'),
            ('res_id', '=', attendance_id),
        ])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.deleted_by_id, self.env.user)

    def test_hr_delete_limited_by_correction_window(self):
        # Future check-in is inside the 31-day correction window: allowed.
        self.attendance.with_user(self.hr_user).unlink()
        self.assertFalse(self.attendance.exists())
        # Records older than the window cannot be deleted by HR.
        old = self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': self.employee.id,
            'check_in': '2015-01-02 08:00:00',
            'check_out': '2015-01-02 16:00:00',
            'presenly_source': 'mobile',
        })
        with self.assertRaisesRegex(ValidationError, 'correction window'):
            old.with_user(self.hr_user).unlink()
        self.assertTrue(old.exists())

    def test_hr_event_unlink_limited_to_failed_evidence(self):
        success = self.env['presenly.attendance.event'].create({
            'employee_id': self.employee.id,
            'attendance_id': self.attendance.id,
            'event_type': 'check_in',
            'source': 'mobile',
            'validation_status': 'success',
        })
        failed = self.env['presenly.attendance.event'].create({
            'employee_id': self.employee.id,
            'attendance_id': self.attendance.id,
            'event_type': 'check_out',
            'source': 'mobile',
            'validation_status': 'failed',
        })
        with self.assertRaisesRegex(UserError, 'only delete failed evidence'):
            success.with_user(self.hr_user).unlink()
        with self.assertRaisesRegex(
            UserError, 'Only a Presenly Administrator or HR Officer'
        ):
            failed.with_user(self.employee_user).unlink()
        failed.with_user(self.hr_user).unlink()
        self.assertFalse(failed.exists())
        self.assertTrue(success.exists())

    def test_form_has_one_timestamp_summary_and_evidence_sections(self):
        result = self.env['hr.attendance'].with_user(self.employee_user).get_view(
            view_id=self.env.ref('hr_attendance.hr_attendance_view_form').id,
            view_type='form',
        )
        root = etree.fromstring(result['arch'].encode())
        self.assertEqual(len(root.xpath("//field[@name='check_in']")), 1)
        self.assertEqual(len(root.xpath("//field[@name='check_out']")), 1)
        self.assertEqual(
            len(root.xpath("//separator[@string='Check-In Evidence']")), 1,
        )
        self.assertEqual(
            len(root.xpath("//separator[@string='Check-Out Evidence']")), 1,
        )
        context_separator = root.xpath(
            "//separator[@string='Attendance Context']"
        )[0]
        check_in_separator = root.xpath(
            "//separator[@string='Check-In Evidence']"
        )[0]
        self.assertLess(
            len(context_separator.xpath('preceding::*')),
            len(check_in_separator.xpath('preceding::*')),
        )
        metadata = root.xpath("//group[@name='presenly_attendance_metadata']")[0]
        self.assertLess(
            len(metadata.xpath('preceding::*')),
            len(check_in_separator.xpath('preceding::*')),
        )
        employee_fields = root.xpath("//field[@name='employee_id']")
        self.assertEqual(len(employee_fields), 1)
        self.assertEqual(
            employee_fields[0].get('readonly'),
            'not presenly_can_change_employee',
        )
        self.assertEqual(
            len(root.xpath("//group[@name='check_in_group']//field[@name='check_in']")),
            0,
        )
        self.assertEqual(
            len(root.xpath("//group[@name='check_out_group']//field[@name='check_out']")),
            0,
        )
        self.assertEqual(root.get('create'), '0')
        self.assertEqual(root.get('edit'), '0')
        self.assertEqual(root.get('delete'), '0')
        selfie_fields = root.xpath(
            "//field[@name='presenly_selfie_in_attachment_id' or "
            "@name='presenly_selfie_out_attachment_id']"
        )
        self.assertEqual(len(selfie_fields), 2)
        self.assertTrue(all(
            field.get('widget') == 'presenly_attachment_image_viewer'
            for field in selfie_fields
        ))

    def test_work_location_policy_is_clear_and_uses_only_operational_routing(self):
        result = self.env['hr.work.location'].get_view(
            view_id=self.env.ref('hr.hr_work_location_form_view').id,
            view_type='form',
        )
        root = etree.fromstring(result['arch'].encode())
        self.assertEqual(
            len(root.xpath(
                "//separator[@string='Presenly Mobile Attendance Policy']"
            )),
            1,
        )
        self.assertEqual(
            len(root.xpath("//separator[@string='Approval Routing']")),
            1,
        )
        self.assertEqual(
            len(root.xpath("//field[@name='presenly_manager_id']")),
            1,
        )
        self.assertEqual(
            len(root.xpath("//field[@name='presenly_approver_ids']")),
            0,
        )

    def test_mobile_color_uses_evidence_not_technical_mode(self):
        address = self.env['res.partner'].create({
            'name': 'Attendance Color Address',
            'company_id': self.company.id,
        })
        location = self.env['hr.work.location'].create({
            'name': 'Attendance Color Location',
            'company_id': self.company.id,
            'address_id': address.id,
        })
        attendance = self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': self.employee.id,
            'check_in': '2030-01-04 08:00:00',
            'check_out': '2030-01-04 16:00:00',
            'presenly_source': 'mobile',
            'presenly_work_location_id': location.id,
            'in_mode': 'technical',
            'out_mode': 'technical',
        })
        for event_type in ('check_in', 'check_out'):
            self.env['presenly.attendance.event'].create({
                'employee_id': self.employee.id,
                'attendance_id': attendance.id,
                'event_type': event_type,
                'work_location_id': location.id,
                'source': 'mobile',
                'validation_status': 'success',
            })
        attendance.invalidate_recordset(['color'])
        self.assertEqual(attendance.color, 10)
        attendance.presenly_event_ids.filtered(
            lambda event: event.event_type == 'check_out'
        ).write({'validation_status': 'failed'})
        attendance.invalidate_recordset(['color'])
        self.assertEqual(attendance.color, 1)
