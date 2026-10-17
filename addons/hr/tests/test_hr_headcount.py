# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged('headcount')
class TestHeadcount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        def lsplit(lst):
            return lst[0], lst[1:]

        super().setUpClass()
        # create 2 companies with distinct resource names and ressource calendars.
        cls.company_us = cls.add_class_company('base.test_company', {'name': 'US'})
        cls.company_be = cls.add_class_company('base.test_company_template', {'name': 'BE'})

        # create 4 resource calendars with distinct working hours.
        cls.resource_40h, cls.resource_35h, cls.resource_65h, cls.resource_30h = \
            cls.env['resource.calendar'].create([{
                'name': '40h',
                'company_id': cls.company_us.id,
                'attendance_ids': [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 8,
                    'hour_to': 12,
                }) for i in range(5)] + [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 13,
                    'hour_to': 17,
                }) for i in range(5)],
            }, {
                'name': '35h',
                'company_id': cls.company_us.id,
                'attendance_ids': [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 8,
                    'hour_to': 12,
                }) for i in range(5)] + [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 13,
                    'hour_to': 16,
                }) for i in range(5)],
            }, {
                'name': '65h',
                'company_id': cls.company_us.id,
                'attendance_ids': [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 8,
                    'hour_to': 12,
                }) for i in range(5)] + [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 13,
                    'hour_to': 17,
                }) for i in range(5)] + [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 18,
                    'hour_to': 23,
                }) for i in range(5)],
            }, {
                'name': '30h',
                'company_id': cls.company_us.id,
                'attendance_ids': [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 8,
                    'hour_to': 12,
                }) for i in range(5)] + [(0, 0, {
                    'dayofweek': str(i),
                    'hour_from': 13,
                    'hour_to': 15,
                }) for i in range(5)],
            }])

        cls.employee_be, cls.employees_us = lsplit(cls.env['hr.employee'].create([{
            'name': 'Employee BE',
            'company_id': cls.company_be.id,
            'date_version': date(2000, 1, 1),
            'contract_date_start': date(2000, 1, 1),
            'wage': 1000,
            'resource_calendar_id': cls.resource_40h.id,
        }] + [{
            'name': 'Employee %s' % i,
            'company_id': cls.company_us.id,
            'date_version': date(2000 + i // 3, 1, 1),
            'contract_date_start': date(2000 + i // 3, 1, 1),
            'contract_date_end': date(2000 + i // 2, 1, 1) if i % 3 else False,
            'wage': 1000 * (i + 1),
            'resource_calendar_id': cls.resource_40h.id if i % 2 else cls.resource_35h.id,
        } for i in range(10)]))

        # make one contract for the BE employee and make 12 versions for US
        # employees with some employees having two versions.
        # note that the versions are never overlapping if an employee has two versions.
        cls.version_be = cls.employee_be.version_id
        cls.versions_us = cls.employees_us.version_id
        cls.versions_us += cls.env['hr.version'].create([{
            'name': 'Contract 2:%s' % i,
            'employee_id': cls.employees_us[i].id,
            'company_id': cls.company_us.id,
            'date_version': date(2000 + i // 2, 1, 2),
            'contract_date_start': date(2000 + i // 2, 1, 2),
            'contract_date_end': date(2000 + i, 1, 1),
            'wage': 12000 * (i + 1),
            'resource_calendar_id': cls.resource_65h.id if i % 2 else cls.resource_30h.id,
        } for i in range(1, 3)])

    def test_headcount_title_company(self):
        """Test that the headcount name is properly set with the company."""

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date.today(),
        })
        self.assertEqual(headcount.name, 'Headcount for US on the %s' % date.today())
        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_be.id,
            'date_from': date.today(),
        })
        self.assertEqual(headcount.name, 'Headcount for BE on the %s' % date.today())

    def test_headcount_title_date_range(self):
        """Test that the headcount name is properly when a date range is set
        or not."""

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2020, 1, 1),
        })
        self.assertEqual(headcount.name, 'Headcount for US on the 2020-01-01')
        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2020, 1, 1),
            'date_to': date(2020, 1, 1),
        })
        self.assertEqual(headcount.name, 'Headcount for US on the 2020-01-01')
        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2020, 1, 1),
            'date_to': date(2020, 1, 31),
        })
        self.assertEqual(headcount.name, 'Headcount for US from 2020-01-01 to 2020-01-31')

    def test_company_consistency(self):
        """Test that the headcount is consistent with the company of the
        versions that are actually taken into account.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_be.id,
            'date_from': date(1900, 1, 1),
            'date_to': date(2100, 1, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_be)
        self.assertEqual(headcount.employee_count, 1)

    def test_headcount_population_large_range(self):
        """Test that the headcount can be populated with a large range of
        dates. This test is also used to check the working rates of the
        versions. In addition to that it checks that the versions that are
        draft or cancelled and the versions of other companies are not taken
        into account.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(1900, 1, 1),
            'date_to': date(2100, 1, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_us)
        self.assertEqual(headcount.employee_count, 10)
        all_headcount_working_rates = self.env['hr.headcount.working.rate'].search([], order='rate')
        self.assertEqual(all_headcount_working_rates.mapped('rate'), [30.0, 35.0, 40.0, 65.0])
        assert self.version_be not in headcount.line_ids.mapped('version_id')
        first_versions = self.env['hr.version']
        for versions in self.versions_us.grouped('employee_id').values():
            first_versions |= versions[-1]
        self.assertEqual(first_versions, headcount.line_ids.mapped('version_id'))

    def test_headcount_population_no_range(self):
        """Test that the headcount can be populated without a range of dates
        to ensure that the headcount is working properly with no end date.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2000, 1, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_us)
        self.assertEqual(headcount.employee_count, 3)
        self.assertEqual(headcount.line_ids.version_id, self.versions_us[0:3])

    def test_headcount_population_no_versions_started(self):
        """Test that the headcount can be populated where no versions have
        started in the selected range to ensure that the headcount is still
        consistent and don't take into account the versions that haven't
        started yet.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(1999, 1, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.employee_count, 0)

    def test_headcount_population_some_versions_over(self):
        """Test that the headcount can be populated where some versions are
        over in the selected range to ensure that the headcount is still
        consistent and don't take into account the versions that are over.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2001, 1, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_us)
        self.assertEqual(headcount.employee_count, 6)
        self.assertEqual(
            headcount.line_ids.version_id,
            self.versions_us[0] | self.versions_us[2:6] | self.versions_us[10]
        )

    def test_headcount_population_only_indefinite_versions(self):
        """Test that the headcount can be populated properly where all the
        versions are indefinite in the selected range.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2020, 2, 1),
        })
        self.assertEqual(headcount.employee_count, 0)
        self.assertEqual(headcount.line_ids, self.env['hr.headcount.line'])
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_us)
        self.assertEqual(headcount.employee_count, 4)
        self.assertEqual(
            headcount.line_ids.version_id,
            self.versions_us[0] | self.versions_us[3] | self.versions_us[6] | self.versions_us[9]
        )

    def test_headcount_population_small_range(self):
        """Test that the headcount can be populated with a small range of
        dates.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2000, 1, 1),
            'date_to': date(2000, 1, 2),
        })
        self.assertEqual(headcount.employee_count, 0)
        headcount.action_populate()
        self.assertEqual(headcount.line_ids.mapped('version_id.company_id'), self.company_us)
        self.assertEqual(headcount.employee_count, 3)
        self.assertEqual(
            headcount.line_ids.version_id,
            self.versions_us[0] | self.versions_us[2] | self.versions_us[10]
        )

    def test_headcount_population_without_employee(self):
        """Test that versions without an employee are not included in the headcount."""
        company = self.env['res.company'].create({
            'name': 'TestHeadcount Company',
        })

        self.env['hr.version'].create({
            'name': False,
            'employee_id': False,
            'company_id': company.id,
            'contract_date_start': date(2026, 3, 1),
        })

        headcount = self.env['hr.headcount'].create({
            'company_id': company.id,
            'date_from': date(2026, 3, 1),
            'date_to': date(2026, 3, 31),
        })

        headcount.action_populate()
        self.assertFalse(headcount.line_ids)
        self.assertEqual(headcount.employee_count, 0)

    def test_headcount_repopulate(self):
        """Test that the headcount can be repopulated.
        And that the values are actually updated.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(2000, 1, 1),
            'date_to': date(2000, 1, 1),
        })
        headcount.action_populate()
        self.assertEqual(headcount.employee_count, 3)
        headcount.write({'date_to': date(2020, 1, 1)})
        headcount.action_populate()
        self.assertEqual(headcount.employee_count, 10)

    def test_special_fields_coherence(self):
        """These tests are here to ensure that the set by the action_populate
        method are coherent with the versions and their orders that are
        actually taken into account.
        """

        headcount = self.env['hr.headcount'].create({
            'company_id': self.company_us.id,
            'date_from': date(1900, 1, 1),
            'date_to': date(2100, 1, 1),
        })
        headcount.action_populate()
        versions_by_employee = self.versions_us.grouped('employee_id')
        headcount_lines_by_employee = headcount.line_ids.grouped('employee_id')
        for employee_id, versions in versions_by_employee.items():
            # verify uniqueness of the lines.
            self.assertEqual(len(headcount_lines_by_employee[employee_id]), 1)
            # verify the working rates of the versions.
            self.assertEqual(
                set(headcount_lines_by_employee[employee_id].working_rate_ids.mapped('rate')),
                {round(version.resource_calendar_id.hours_per_week, 2) for version in versions}
            )
