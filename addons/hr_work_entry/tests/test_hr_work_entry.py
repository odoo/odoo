# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestHrWorkEntry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two companies
        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.env.user.company_ids = [(6, 0, [cls.company_a.id, cls.company_b.id])]
        cls.env.user.company_id = cls.company_a.id
        # Create an employee for each company
        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Employee A',
            'company_id': cls.company_a.id,
            'contract_date_start': '2023-01-01',
            'date_version': '2023-01-01',
        })
        cls.employee_a_first_version = cls.employee_a.version_ids[0]
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': cls.company_b.id,
            'contract_date_start': '2023-01-01',
            'date_version': '2023-01-01',
        })
        # Create a work entry type
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Attendance',
            'code': 'ATTEND',
        })

    def test_work_entry_company_from_employee(self):
        """Test that work entry uses employee's company not the current user's company in vals."""
        work_entry = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry',
            'employee_id': self.employee_b.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date': date(2024, 1, 1),
            'duration': 8,
        })
        self.assertEqual(
            work_entry.company_id, self.employee_b.company_id,
            "Work entry should use the employee's company not the current user's company.",
        )

    def test_work_entry_conflict_no_we_type(self):
        """Test that work entry conflicts with no work entry type."""
        work_entry = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry',
            'work_entry_type_id': False,
            'employee_id': self.employee_b.id,
            'date': date(2024, 1, 1),
            'duration': 8,
        })
        self.assertEqual(
            work_entry.state, 'conflict',
            "Work entry should conflict with no work entry type.",
        )
        work_entry = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry',
            'work_entry_type_id': self.work_entry_type.id,
            'employee_id': self.employee_b.id,
            'date': date(2024, 1, 1),
            'duration': 8,
        })
        self.assertEqual(
            work_entry.state, 'draft',
            "Work entry should not conflict with a work entry type.",
        )
        work_entry.write({'work_entry_type_id': False})
        self.assertEqual(
            work_entry.state, 'conflict',
            "Work entry should conflict with no work entry type.",
        )

    def test_work_entry_conflict_sum_duration(self):
        """Test that work entry conflicts when the duration for one day is <= 0h or > 24h."""
        with self.assertRaises(ValidationError), mute_logger('odoo.sql_db'):
            self.env['hr.work.entry'].create({
                'name': 'Test Work Entry',
                'work_entry_type_id': False,
                'employee_id': self.employee_b.id,
                'date': date(2024, 1, 1),
                'duration': 0,
            })

        work_entry = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry',
            'work_entry_type_id': self.work_entry_type.id,
            'employee_id': self.employee_b.id,
            'date': date(2024, 1, 1),
            'duration': 8,
        })
        self.assertEqual(
            work_entry.state, 'draft',
            "Work entry should be in draft.",
        )
        work_entry_2 = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry 2',
            'work_entry_type_id': self.work_entry_type.id,
            'employee_id': self.employee_b.id,
            'date': date(2024, 1, 1),
            'duration': 17,
        })
        self.assertEqual(
            (work_entry | work_entry_2).mapped('state'), ['conflict', 'conflict'],
            "Work entries with a total duration for a same day <= 0h or > 24h should conflict.",
        )
        work_entry_2.write({
            'duration': 16,
        })
        self.assertEqual(
            (work_entry | work_entry_2).mapped('state'), ['draft', 'draft'],
            "Work entries with a total duration for a same day > 0h and <= 24h should not conflict.",
        )

    def test_nullify_work_entry_tz(self):
        """
        Test that the work entries of the previous month are not affected when regenerating the next month work entries
        no matter what's the timezone of the employee
        """
        self.employee_a.tz = 'Europe/Brussels'
        self.employee_a.resource_calendar_id.tz = 'Europe/Brussels'

        january_work_entries = self.employee_a.generate_work_entries(date(2024, 1, 1), date(2024, 1, 31), force=True)
        self.employee_a.generate_work_entries(date(2024, 2, 1), date(2024, 2, 28), force=True)

        new_january_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_a.id),
            ('date', '>=', date(2024, 1, 1)),
            ('date', '<=', date(2024, 1, 31)),
        ])
        self.assertEqual(january_work_entries, new_january_work_entries)

    def test_nullify_work_entry(self):
        """
        Test that we correctly nullify the work entries that were previously generated when we add a new version
        """
        january_work_entries = self.employee_a.generate_work_entries(date(2024, 1, 1), date(2024, 1, 31))
        self.assertTrue(all(we.version_id == self.employee_a_first_version for we in january_work_entries))

        second_version = self.employee_a.create_version({
            'date_version': date(2023, 12, 1)
        })
        self.employee_a.generate_work_entries(date(2024, 1, 1), date(2024, 1, 31))

        all_january_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_a.id),
            ('date', '>=', date(2024, 1, 1)),
            ('date', '<=', date(2024, 1, 31)),
        ])

        self.assertEqual(len(all_january_work_entries), 23)
        self.assertTrue(all(we.version_id == second_version for we in all_january_work_entries))

    def test_work_entry_version_id(self):
        """
        Test that we correctly set the version_id field of the work entry depending on the date
        """
        second_version = self.employee_a.create_version({
            'date_version': date(2023, 12, 1)
        })

        v1_we, v2_we = self.env['hr.work.entry'].create([
            {
                'date': date(2023, 10, 1),
                'employee_id': self.employee_a.id,
            },
            {
                'date': date(2024, 1, 1),
                'employee_id': self.employee_a.id,
            }
        ])
        self.assertEqual(v1_we.version_id, self.employee_a_first_version)
        self.assertEqual(v2_we.version_id, second_version)
