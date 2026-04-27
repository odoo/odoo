# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nUsHrPayrollADPExport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        def create_work_entry(employee, work_entry_type, start, stop):
            a = {
                'name': 'Work entry test',
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'date_start': start,
                'date_stop': stop,
                'company_id': cls.us_company.id,
                'state': 'validated'
            }
            return a

        super().setUpClass()
        cls.us_company = cls.env['res.company'].create({
            'name': 'My US Company - TEST',
            'country_id': cls.env.ref('base.us').id,
            'l10n_us_adp_code': "US123"
        })

        cls.hourly_employee = cls.env['hr.employee'].create({
            'name': "John Hourly",
            'l10n_us_adp_code': "ABC1",
            'company_id': cls.us_company.id
        })
        cls.monthly_employee = cls.env['hr.employee'].create({
            'name': "John Monthly",
            'l10n_us_adp_code': "ABC2",
            'company_id': cls.us_company.id
        })

        cls.hourly_contract = cls.env['hr.contract'].create({
            'name': "Hourly Contract",
            'employee_id': cls.hourly_employee.id,
            'wage_type': 'hourly',
            'hourly_wage': 40,
            'wage': 1000,
            'date_start': date(2023, 1, 1),
            'state': 'open'
        })

        cls.hourly_contract = cls.env['hr.contract'].create({
            'name': "Monthly Contract",
            'employee_id': cls.monthly_employee.id,
            'wage_type': 'monthly',
            'wage': 10000,
            'date_start': date(2023, 1, 1),
            'state': 'open'
        })

        cls.work_100_work_entry = cls.env['hr.work.entry.type'].search([('code', '=', 'WORK100')])
        cls.overtime_work_entry = cls.env['hr.work.entry.type'].search([('code', '=', 'OVERTIME')])
        cls.work_100_work_entry.write({
            'external_code': "ADP_100"
        })
        cls.overtime_work_entry.write({
            'external_code': "ADP_200"
        })

        cls.adp_work_entry_holidays = cls.env['hr.work.entry.type'].create({
            'name': 'ADP Holidays',
            'code': 'WORKTEST1',
            'external_code': "ADP1"
        })

        cls.adp_work_entry_sick = cls.env['hr.work.entry.type'].create({
            'name': 'ADP Sick',
            'code': 'WORKTEST2',
            'external_code': "ADP2"
        })
        hourly_sick_days = [4, 17]
        monthly_holidays = [11, 12, 13, 14, 15]
        work_entries = []
        for i in range(1, 31):
            if i not in hourly_sick_days:
                work_entries.append(create_work_entry(cls.hourly_employee,
                                                      cls.work_100_work_entry,
                                                      datetime(2024, 1, i, 8, 0, 0),
                                                      datetime(2024, 1, i, 18, 0, 0)))
                work_entries.append(create_work_entry(cls.hourly_employee,
                                                      cls.overtime_work_entry,
                                                      datetime(2024, 1, i, 18, 0, 0),
                                                      datetime(2024, 1, i, 20, 0, 0)))
            else:
                work_entries.append(create_work_entry(cls.hourly_employee,
                                                      cls.adp_work_entry_sick,
                                                      datetime(2024, 1, i, 8, 0, 0),
                                                      datetime(2024, 1, i, 18, 0, 0)))

            if i not in monthly_holidays:
                work_entries.append(create_work_entry(cls.monthly_employee,
                                                      cls.work_100_work_entry,
                                                      datetime(2024, 1, i, 8, 0, 0),
                                                      datetime(2024, 1, i, 17, 0, 0)))
            else:
                work_entries.append(create_work_entry(cls.monthly_employee,
                                                      cls.adp_work_entry_holidays,
                                                      datetime(2024, 1, i, 8, 0, 0),
                                                      datetime(2024, 1, i, 17, 0, 0)))

        cls.work_entry_ids = cls.env['hr.work.entry'].create(work_entries)

    def test_export(self):

        adp_export = self.env['l10n.us.adp.export'].with_company(self.us_company).create({
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 1, 31),
            'company_id': self.us_company.id,
            'batch_id': 'ADPEXPORT1',
            'batch_description': 'Test Export',
            'employee_ids': [self.monthly_employee.id, self.hourly_employee.id]
        })
        expected_header = ['Co Code', 'Batch ID', 'File  #', 'Employee Name', 'Batch Description', 'Rate', 'Regular Hours', 'Regular Earnings', 'Overtime Hours', 'Overtime Earnings', 'ADP Sick ADP2', 'ADP Sick Hours-ADP2', 'ADP Sick Earnings-ADP2', 'ADP Holidays ADP1', 'ADP Holidays Hours-ADP1', 'ADP Holidays Earnings-ADP1']
        expected_rows = [
            ['US123', 'ADPEXPORT1', 'ABC1', 'John Hourly', 'Test Export', 40.0, 280.0, 0, 56.0, 0, 'ADP2', 20.0, '', '', '', ''],
            ['US123', 'ADPEXPORT1', 'ABC2', 'John Monthly', 'Test Export', 10000.0, 225.0, 8333.33, 0, 0, '', '', '', 'ADP1', 45.0, 1666.67],
        ]
        result = adp_export._generate_rows()
        result_header = result[0]
        result_rows = sorted(result[1:], key=lambda x: x[2])

        self.assertListEqual(expected_header, result_header)
        self.assertListEqual(expected_rows, result_rows)

        adp_export.action_generate_csv()

        self.assertEqual(adp_export.csv_filename, "EPIUS12301.csv")
