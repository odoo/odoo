# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWorkEntryType(TransactionCase):

    def test_duplicate_work_entry_type_same_country(self):
        country_be = self.env.ref('base.be')
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_be.id,

        })
        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types with the same code in the same country",
        ):
            self.env['hr.work.entry.type'].create({
                'code': 'test123',
                'name': "Test we type",
                'country_id': country_be.id,
            })

        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types at the same time with the same code in the same country",
        ):
            self.env['hr.work.entry.type'].create([
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': country_be.id,
                },
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': country_be.id,
                },
            ])

    def test_duplicate_work_entry_type_all_countries(self):
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': False,

        })
        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types with the same code for all countries",
        ):
            self.env['hr.work.entry.type'].create({
                'code': 'test123',
                'name': "Test we type",
                'country_id': False,
            })

        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types at the same time with the same code for all countries",
        ):
            self.env['hr.work.entry.type'].create([
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': False,
                },
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': False,
                },
            ])

    def test_unique_work_entry_types(self):
        """
        No error should be raised if the work entry codes are unique per country_id
        """
        country_be = self.env.ref('base.be')
        country_us = self.env.ref('base.us')

        # creating them one by one. `self` should contain one record only
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_be.id,

        })
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_us.id,
        })
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': False
        })

        # creating them in batch. `self` should have multiple records at once
        self.env['hr.work.entry.type'].create([
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': False,
            },
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': country_us.id,
            },
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': country_be.id,
            },
        ])

    def test_copy_work_entry_type_generates_unique_code(self):
        """
        Test that copying a work entry type generates a unique code automatically
        """
        country_us = self.env.ref('base.us')
        work_entry_us = self.env['hr.work.entry.type'].create({
            'code': "MYTEST",
            'name': "My Test",
            'country_id': country_us.id,
        })

        copies = work_entry_us.copy()
        self.assertNotEqual(copies.code, work_entry_us.code)
        self.assertTrue(copies.code.startswith("MYTEST_"))
        self.assertEqual(self.env['hr.work.entry.type'].search_count([('code', '=', copies.code)]), 1)

    def test_get_default_attendance_ids_transfers_work_entry_type(self):
        """ Calendar copies built from a company's calendar must carry over the
        attendances' work_entry_type_id, not just their hours. """
        company = self.env['res.company'].create({'name': 'Test Co'})
        work_entry_type = self.env['hr.work.entry.type'].create({
            'code': 'TESTATT',
            'name': 'Test Attendance',
            'country_id': False,
        })
        company.resource_calendar_id.attendance_ids.write({'work_entry_type_id': work_entry_type.id})

        new_calendar = self.env['resource.calendar'].create({
            'name': 'Copied Calendar',
            'company_id': company.id,
            'attendance_ids': self.env['resource.calendar']._get_default_attendance_ids(company),
        })
        self.assertTrue(new_calendar.attendance_ids)
        self.assertEqual(set(new_calendar.attendance_ids.mapped('work_entry_type_id')), {work_entry_type}, "All copied attendances should reference the source work_entry_type_id")

    def test_copy_work_entry_type_different_countries(self):
        """
        Test that copying work entry types with different countries generates unique codes
        """
        country_us = self.env.ref('base.us')
        country_be = self.env.ref('base.be')

        work_entry_us, work_entry_be = self.env['hr.work.entry.type'].create([
            {
                'code': "MYTEST",
                'name': "My Test US",
                'country_id': country_us.id,
            },
            {
                'code': "MYTEST",
                'name': "My Test BE",
                'country_id': country_be.id,
            }
        ])

        work_entry_us_copy = work_entry_us.copy()
        work_entry_be_copy = work_entry_be.copy()

        self.assertEqual(work_entry_us_copy.country_id, country_us)
        self.assertEqual(work_entry_be_copy.country_id, country_be)

        self.assertNotEqual(work_entry_us_copy.code, work_entry_us.code)
        self.assertNotEqual(work_entry_be_copy.code, work_entry_be.code)

        self.assertEqual(self.env['hr.work.entry.type'].search_count([('code', '=', work_entry_us_copy.code)]), 1)
        self.assertEqual(self.env['hr.work.entry.type'].search_count([('code', '=', work_entry_be_copy.code)]), 1)
