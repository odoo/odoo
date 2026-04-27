# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.tests import tagged
from .common import TestSdworxExportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSdWorxWizard(TestSdworxExportCommon):

    def test_global_time_off_sd_worx(self):
        self.env.user.tz = 'Europe/Brussels'
        self.holiday_leave_types.write({
            'work_entry_type_id': self.pto_work_entry_type.id,
            'leave_validation_type': 'no_validation',
        })

        self.env['hr.leave.allocation'].create({
            'name': 'Georges allocation',
            'holiday_status_id': self.holiday_leave_types.id,
            'number_of_days': 25,
            'employee_id': self.employee_georges.id,
            'date_from': '2026-01-01',
        }).action_approve()

        self.env['hr.leave'].create({
            'name': 'Full month',
            'employee_id': self.employee_georges.id,
            'holiday_status_id': self.holiday_leave_types.id,
            'request_date_from': '2026-01-01',
            'request_date_to': '2026-01-31',
        })

        self.env['resource.calendar.leaves'].create({
            'date_from': '2026-01-12 00:00:00',
            'date_to': '2026-01-12 23:59:59',
            'work_entry_type_id': self.gto_work_entry_type.id,
            'calendar_id': self.employee_georges.resource_calendar_id.id,
        })

        export_wizard = self.env['l10n_be.export.sdworx.leaves.wizard'].create({
            'reference_month': '1',
            'reference_year': 2026,
        })

        export_wizard.action_generate_export_file()

        content = base64.b64decode(export_wizard.export_file).decode('utf-8')

        expected_line_am = '12345670000001K2026011270100360'
        expected_line_pm = '12345670000001K2026011270100400'

        self.assertIn(expected_line_am, content)
        self.assertIn(expected_line_pm, content)
