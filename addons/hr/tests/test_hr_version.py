# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from psycopg2.errors import CheckViolation

from odoo.tests import tagged
from odoo.tests.common import TransactionCase, freeze_time
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestHrVersion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_dates_constraints(self):
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01'
        })
        self.assertFalse(employee.contract_date_start)
        self.assertFalse(employee.contract_date_end)

        employee.write({
            'contract_date_start': '2020-01-01',
            'contract_date_end': False
        })
        self.assertEqual(employee.contract_date_start, date(2020, 1, 1))
        self.assertFalse(employee.contract_date_end)

        employee.write({
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31'
        })
        self.assertEqual(employee.contract_date_start, date(2020, 1, 1))
        self.assertEqual(employee.contract_date_end, date(2020, 12, 31))

        employee.write({
            'contract_date_start': False,
            'contract_date_end': False
        })
        self.assertFalse(employee.contract_date_start)
        self.assertFalse(employee.contract_date_end)

        with self.assertRaises(CheckViolation), mute_logger('odoo.sql_db'):
            employee.write({
                'contract_date_start': False,
                'contract_date_end': '2020-12-31'
            })

        with self.assertRaises(ValidationError):
            employee.write({
                'contract_date_start': '2021-01-01',
                'contract_date_end': '2020-12-31'
            })

    def test_contracts_no_overlap(self):
        # Simple overlap cases
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31'
        })

        with self.assertRaises(ValidationError):
            employee.create_version({
                'date_version': '2019-06-01',
                'contract_date_start': '2019-06-01',
                'contract_date_end': '2020-05-31'
            })

        with self.assertRaises(ValidationError):
            employee.create_version({
                'date_version': '2020-06-01',
                'contract_date_start': '2020-06-01',
                'contract_date_end': '2021-05-31'
            })

        with self.assertRaises(ValidationError):
            employee.create_version({
                'date_version': '2020-02-01',
                'contract_date_start': '2020-02-01',
                'contract_date_end': '2020-10-31'
            })

        # It should not detect overlap with archived versions
        employee.create_version({
            'active': False,
            'date_version': '2019-06-01',
            'contract_date_start': '2019-06-01',
            'contract_date_end': '2020-05-31'
        })

    def test_occupation_dates(self):
        """
        Occupation dates are global for the employee, they are a list of intervals
        (date_from, date_to) where the employee is in contract (date_from and date_to included).
        """
        # A single version and no contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01'
        })
        self.assertEqual(employee._get_all_contract_dates(), [])

        # A single version and contract
        employee.write({
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31'
        })
        occupation_dates = [(date(2020, 1, 1), date(2020, 12, 31))]
        self.assertEqual(employee._get_all_contract_dates(), occupation_dates)

        # 2 versions with 1 contract each
        employee.create_version({
            'date_version': '2021-01-01',
            'contract_date_start': '2021-01-01',
            'contract_date_end': '2023-12-31'
        })
        occupation_dates = [
            (date(2020, 1, 1), date(2020, 12, 31)),
            (date(2021, 1, 1), date(2023, 12, 31)),
        ]
        self.assertEqual(employee._get_all_contract_dates(), occupation_dates)

        # 3 versions with 2 sharing the same contract
        employee.create_version({
            'date_version': '2022-01-01',
        })
        self.assertEqual(employee._get_all_contract_dates(), occupation_dates)

        # 4 versions with 2 sharing the same contract, the last one is permanent
        employee.create_version({
            'date_version': '2025-01-01',
            'contract_date_start': '2025-01-01',
        })
        occupation_dates = [
            (date(2020, 1, 1), date(2020, 12, 31)),
            (date(2021, 1, 1), date(2023, 12, 31)),
            (date(2025, 1, 1), False),
        ]
        self.assertEqual(employee._get_all_contract_dates(), occupation_dates)

    def test_dates_new_version_out_of_contract(self):
        """
        If the new version falls on a period out of contract, clear the dates
        """
        # Create a new version after the end of the current contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
        })

        version = employee.create_version({
            'date_version': '2021-01-01'
        })
        self.assertFalse(version.contract_date_start)
        self.assertFalse(version.contract_date_end)

        # Forcing the contract_date_start and or contract_date_end in the 'create' should override False
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
        })

        version = employee.create_version({
            'date_version': '2021-01-01',
            'contract_date_start': '2021-01-01',
            'contract_date_end': '2021-12-31'
        })
        self.assertEqual(version.contract_date_start, date(2021, 1, 1))
        self.assertEqual(version.contract_date_end, date(2021, 12, 31))

        # Create a new version before the start of the current contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
        })

        version = employee.create_version({'date_version': '2019-01-01'})
        self.assertFalse(version.contract_date_start)
        self.assertFalse(version.contract_date_end)

        # Create a new version between two contracts
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31'
        })

        employee.create_version({
            'date_version': '2022-01-01',
            'contract_date_start': '2022-01-01',
            'contract_date_end': '2022-12-31'
        })

        version = employee.create_version({
            'date_version': '2021-01-01',
        })
        self.assertFalse(version.contract_date_start)
        self.assertFalse(version.contract_date_end)

    def test_dates_new_version_in_contract(self):
        """
        If the new version falls on some contract, copy its contract dates
        """
        # Create a new version on a permanent contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
        })

        version = employee.create_version({
            'date_version': '2021-01-01'
        })
        self.assertEqual(version.contract_date_start, date(2020, 1, 1))
        self.assertFalse(version.contract_date_end)

        # Create a new version on a fixed term contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2021-12-31'
        })

        version = employee.create_version({'date_version': '2021-01-01'})
        self.assertEqual(version.contract_date_start, date(2020, 1, 1))
        self.assertEqual(version.contract_date_end, date(2021, 12, 31))

        # Create a new version on any contract interval regardless of the version valid at that date
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31'
        })

        employee.create_version({
            'date_version': '2022-01-01',
            'contract_date_start': '2021-01-01',
            'contract_date_end': '2022-12-31'
        })

        version = employee.create_version({
            'date_version': '2021-01-01',
        })
        self.assertEqual(version.contract_date_start, date(2021, 1, 1))
        self.assertEqual(version.contract_date_end, date(2022, 12, 31))

    def test_dates_synchronisation(self):
        """
        All versions that share or will share (at the end of a 'write')
        the same contract_date_start are synchronized.
        """
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2021-12-31',
        })
        v1 = employee.version_id

        v2 = employee.create_version({
            'date_version': '2021-01-01',
            'contract_date_end': '2022-12-31',
        })
        self.assertEqual(v2.contract_date_end, date(2022, 12, 31))
        self.assertEqual(v1.contract_date_end, v2.contract_date_end)

        v1.write({
            'contract_date_start': '2021-01-01',
        })
        self.assertEqual(v1.contract_date_start, date(2021, 1, 1))
        self.assertEqual(v1.contract_date_start, v2.contract_date_start)

        v2.write({
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
        })
        self.assertEqual(v2.contract_date_start, date(2020, 1, 1))
        self.assertEqual(v1.contract_date_start, v2.contract_date_start)
        self.assertEqual(v2.contract_date_end, date(2020, 12, 31))
        self.assertEqual(v1.contract_date_end, v2.contract_date_end)

        v3 = employee.create_version({
            'date_version': '2030-01-01',
            'contract_date_start': '2030-01-01',
        })
        versions = []
        for i in range(10):
            versions.append(employee.create_version({
                'date_version': f'20{31 + i}-01-01',
            }))
        v3.write({
            'contract_date_end': '2040-12-31',
        })
        for version in versions:
            self.assertEqual(version.contract_date_end, date(2040, 12, 31))

        v4 = employee.create_version({
            'date_version': '2050-01-01',
            'contract_date_start': '2050-01-01',
            'contract_date_end': '2050-12-31',
        })
        v5 = employee.create_version({
            'date_version': '2051-01-01',
            'contract_date_start': '2051-01-01',
            'contract_date_end': '2051-12-31',
        })
        v5.write({
            'contract_date_start': '2050-01-01',
        })
        self.assertEqual(v4.contract_date_end, date(2051, 12, 31))

    def test_in_out_contract(self):
        """
        Check that an employee is in or out of the contract at a specific date.
        """
        # If no contract dates are defined, the employee is not considered in contract
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
        })
        self.assertFalse(employee._is_in_contract(date(2010, 1, 1)))
        self.assertFalse(employee._is_in_contract(date(2020, 1, 1)))
        self.assertFalse(employee._is_in_contract(date(2030, 1, 1)))

        # In a permanent contract, the employee is contract since the contract_date_start
        employee.contract_date_start = '2020-01-01'
        self.assertFalse(employee._is_in_contract(date(2010, 1, 1)))
        self.assertTrue(employee._is_in_contract(date(2020, 1, 1)))
        self.assertTrue(employee._is_in_contract(date(2030, 1, 1)))

        # In a fixed term contract, the employee is contract in between the contract dates
        employee.contract_date_end = '2029-12-31'
        self.assertFalse(employee._is_in_contract(date(2010, 1, 1)))
        self.assertTrue(employee._is_in_contract(date(2020, 1, 1)))
        self.assertFalse(employee._is_in_contract(date(2030, 1, 1)))

    def test_cron_update_current_version(self):
        cron = self.env.ref('hr.ir_cron_data_employee_update_current_version')

        with freeze_time(date(2020, 1, 1)), self.enter_registry_test_mode():
            employee = self.env['hr.employee'].create({
                'name': 'John Doe',
                'date_version': '2020-01-01',
            })
            v1 = employee.version_id
            v2 = employee.create_version({
                'date_version': '2020-01-02'
            })
            self.assertEqual(v1, employee.current_version_id)
            cron.method_direct_trigger()
            self.assertEqual(v1, employee.current_version_id)

        with freeze_time(date(2020, 1, 2)), self.enter_registry_test_mode():
            self.assertEqual(v1, employee.current_version_id)
            cron.method_direct_trigger()
            self.assertEqual(v2, employee.current_version_id)

    def test_related_fields_on_version(self):
        """ Some groups have been added to avoid users with basic access to HR app see some critical (like wage field for instance)
            This test makes sure the groups added in version fields is also in the employee fields related.
            However, to define the same groups in employee fields, we have to redefine the related fields (readonly=False, related='version_id.{field_name})
            Otherwise, the field we loose the linked with the version field and could be readonly instead of editable.
        """
        version_fields = {
            f_name: field
            for f_name, field in self.env['hr.version']._fields.items()
            if field.groups and field.groups not in ['hr.group_hr_user', 'base.group_user'] and not (field.related and field.related.startswith('employee_id'))
        }
        employee_fields = {
            f_name: field
            for f_name, field in self.env['hr.employee']._fields.items()
            if f_name in version_fields
        }
        fields_without_group = []
        fields_without_related = []
        fields_readonly = []
        for f_name, field in employee_fields.items():
            v_field = version_fields[f_name]
            if not (field.groups and field.groups != v_field):
                fields_without_group.append(f_name)
            elif not (field.related and field.related == f'version_id.{f_name}'):
                fields_without_related.append(f_name)
            elif field.readonly != v_field.readonly:
                fields_readonly.append(f_name)
        self.assertFalse(fields_without_group, "Inconsistency between some employee fields and version ones (those employees fields should have the same groups than related one in version")
        self.assertFalse(fields_without_related, "Some employee fields have the same name than the version ones but they are not related")
        self.assertFalse(fields_readonly, "(Readonly) Inconsistency between some employee fields and version ones, the both fields (in version and employee) have to be readonly or editable")
