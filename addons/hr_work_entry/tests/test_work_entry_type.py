# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

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

    def test_name_search_finds_by_name_or_code(self):
        """
        Search should match both the name and the payroll code
        """
        absence_type = self.env['hr.work.entry.type'].create({
            'code': 'ABS',
            'name': 'Absence Type',
            'count_as': 'absence',
            'country_id': False,
        })
        working_type = self.env['hr.work.entry.type'].create({
            'code': 'WORK2',
            'name': 'Working Time',
            'count_as': 'working_time',
            'country_id': False,
        })

        names = self.env['hr.work.entry.type'].name_search('Absence')
        self.assertIn(absence_type.id, [result[0] for result in names])

        codes = self.env['hr.work.entry.type'].name_search('WORK2')
        self.assertIn(working_type.id, [result[0] for result in codes])

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

    def test_time_rule_without_country_offers_active_company_types(self):
        country_be = self.env.ref('base.be')
        self.env.company.country_id = country_be
        generic_type = self.env['hr.work.entry.type'].create({'code': 'GENTEST', 'name': "Generic"})
        be_type = self.env['hr.work.entry.type'].create({'code': 'BETEST', 'name': "Belgian", 'country_id': country_be.id})
        rule = self.env['hr.time.rule'].create({
            'name': 'Shared rule',
            'company_id': False,
            'country_id': False,
            'condition_work_entry_type_ids': [(4, generic_type.id)],
        })
        self.assertFalse(rule.country_id)
        self.assertIn(be_type, rule.country_work_entry_type_ids,
            "A rule without company nor country should offer the time types of the active company's country")

    def test_schedule_time_type_domains(self):
        """ The time type dropdowns of the working schedules keep the country domain of the
        model, and the public holidays (absences) are not limited to working time types. """
        def view_domain(model, view_xmlid, view_type):
            arch = self.env[model].get_views([(self.env.ref(view_xmlid).id, view_type)])['views'][view_type]['arch']
            node = etree.fromstring(arch).xpath("//field[@name='work_entry_type_id']")[0]
            return node.get('domain') or self.env[model].fields_get(['work_entry_type_id'])['work_entry_type_id']['domain']

        for view_xmlid, view_type in [
            ('resource.view_resource_calendar_attendance_tree', 'list'),
            ('resource.view_resource_calendar_attendance_form', 'form'),
            ('hr_work_entry.view_resource_calendar_multi_create_form', 'form'),
        ]:
            domain = view_domain('resource.calendar.attendance', view_xmlid, view_type)
            self.assertIn('resource_calendar_selectable', domain, view_xmlid)
            self.assertIn('allowed_work_entry_type_ids', domain, view_xmlid)

        for view_xmlid, view_type in [
            ('resource.resource_calendar_leave_tree', 'list'),
            ('resource.resource_calendar_leave_form', 'form'),
        ]:
            domain = view_domain('resource.calendar.leaves', view_xmlid, view_type)
            self.assertNotIn('resource_calendar_selectable', domain, view_xmlid)
            self.assertIn('allowed_work_entry_type_ids', domain, view_xmlid)

        company = self.env['res.company'].create({'name': 'BE Co', 'country_id': self.env.ref('base.be').id})
        calendar = self.env['resource.calendar'].create({'name': 'BE Calendar', 'company_id': company.id})
        public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'calendar_id': calendar.id,
            'company_id': company.id,
            'date_from': '2031-12-26 00:00:00',
            'date_to': '2031-12-26 23:59:59',
        })
        self.assertEqual(public_holiday.work_entry_type_id.code, '006.00')
        self.assertIn(public_holiday.work_entry_type_id, public_holiday.allowed_work_entry_type_ids)
