# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from psycopg2.errors import CheckViolation

from odoo.tests import tagged
from odoo.tests.common import freeze_time
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import mute_logger

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
class TestHrVersion(TestHrCommon):
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

    def test_1_version_contract_synchronisation(self):
        """
        When an employee has only one version, the contract_date_start should
        be synchronized with the date_version.
        """
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
        })
        version = employee.version_id

        employee.write({'contract_date_start': '2019-01-01'})
        self.assertEqual(version.contract_date_start, version.date_version)

        # date_version should not be reset if the contract_date_start is set to False
        employee.write({'contract_date_start': False})
        self.assertEqual(version.date_version, date(2019, 1, 1))

        employee.write({'contract_date_start': '2021-01-01'})
        self.assertEqual(version.contract_date_start, version.date_version)

    def test_2_versions_contract_synchronisation(self):
        """
        When an employee has two versions, the synchronisation should stop
        """
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
        })
        v1 = employee.version_id

        employee.write({'contract_date_start': '2019-01-01'})
        self.assertEqual(v1.contract_date_start, v1.date_version)

        v2 = employee.create_version({'date_version': '2021-01-01'})
        employee.write({'contract_date_start': '2020-01-01'})
        self.assertEqual(v1.date_version, date(2019, 1, 1))
        self.assertEqual(v2.date_version, date(2021, 1, 1))

        # Archived versions do not count.
        # So if we archive v2, the synchronisation should start again.
        v2.active = False
        employee.write({'contract_date_start': '2021-01-01'})
        self.assertEqual(v1.contract_date_start, v1.date_version)

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

    def test_multi_edit_contract_sync_same_contract(self):
        """
        Test the multi-edit contract sync feature when the targeted versions share the same contract.
        """
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
        })
        versions = employee.version_id
        versions |= employee.create_version({'date_version': '2020-04-01'})
        versions |= employee.create_version({'date_version': '2020-08-01'})

        versions[:2].contract_date_end = "2020-9-30"

        for version in versions:
            self.assertEqual(version.contract_date_end, date(2020, 9, 30))

    def test_multi_edit_contract_sync_different_contract(self):
        """
        Test the multi-edit contract sync feature when the targeted versions have different contracts.
        """
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-5-31',
        })
        versions = employee.version_id
        versions |= employee.create_version({'date_version': '2020-04-01'})
        versions |= employee.create_version({
            'date_version': '2020-08-01',
            'contract_date_start': '2020-08-01',
        })

        with self.assertRaises(ValidationError):
            versions[:2].contract_date_end = "2020-9-30"

    def test_multi_edit_other(self):
        """
        Test the multi-edit when the targeted versions have different contracts
        Different fields than contract_date_start and contract_date_end are changed.
        """
        jobA = self.env['hr.job'].create({'name': "Job A"})
        jobB = self.env['hr.job'].create({'name': "Job B"})

        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-5-31',
            'job_id': jobA.id,
        })
        versions = employee.version_id
        versions |= employee.create_version({'date_version': '2020-04-01'})
        versions |= employee.create_version({
            'date_version': '2020-08-01',
            'contract_date_start': '2020-08-01',
            'job_id': jobA.id,
        })

        versions[1:].job_id = jobB.id

        self.assertEqual(versions[0].job_id.id, jobA.id)
        for version in versions[1:]:
            self.assertEqual(version.job_id.id, jobB.id)

    def test_multi_edit_other_and_contract_date_sync(self):
        """
        Test the multi-edit when the targeted versions have the same contract
        Different contract_dates and other fields are changed.
        """
        jobA = self.env['hr.job'].create({'name': "Job A"})
        jobB = self.env['hr.job'].create({'name': "Job B"})

        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'contract_date_end': '2020-12-31',
            'job_id': jobA.id,
        })
        versions = employee.version_id
        versions |= employee.create_version({'date_version': '2020-04-01'})
        versions |= employee.create_version({'date_version': '2020-08-01'})

        versions[1:].write({
            "contract_date_end": "2020-9-30",
            "job_id": jobB.id,
        })

        self.assertEqual(versions[0].job_id.id, jobA.id)
        self.assertEqual(versions[0].contract_date_end, date(2020, 9, 30))
        for version in versions[1:]:
            self.assertEqual(version.job_id.id, jobB.id)
            self.assertEqual(version.contract_date_end, date(2020, 9, 30))

    def test_delete_version(self):
        employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'date_version': '2020-01-01',
        })
        v1 = employee.version_id
        v2 = employee.create_version({
            'date_version': '2021-01-01',
        })
        v3 = employee.create_version({
            'date_version': '2022-01-01',
        })
        self.assertEqual(employee.current_version_id, v3)

        v3.unlink()
        self.assertEqual(employee.current_version_id, v2)
        v1.unlink()
        self.assertEqual(employee.current_version_id, v2)
        with self.assertRaises(ValidationError):
            v2.unlink()

    def test_multi_edit_multi_employees_no_contract(self):
        """
        Test the multi-edit when there is one version per employee, without contract
        """
        employee_john, employee_rob = self.env['hr.employee'].create([
            {
                'name': 'John Doe',
                'date_version': '2020-01-01',
            },
            {
                'name': 'Rob Carter',
                'date_version': '2020-10-18',
            }
        ])
        versions = (employee_john | employee_rob).version_id
        versions.write({
            'contract_date_start': '2021-10-10'
        })
        self.assertEqual(versions[0].contract_date_start, date(2021, 10, 10))
        self.assertEqual(versions[1].contract_date_start, date(2021, 10, 10))

    def test_multi_edit_multi_employees_mix_contract(self):
        """
        Test the multi-edit when there is one version per employee, some with contract
        """
        employee_john, employee_rob = self.env['hr.employee'].create([
            {
                'name': 'John Doe',
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
            },
            {
                'name': 'Rob Carter',
                'date_version': '2020-10-18',
            }
        ])
        versions = (employee_john | employee_rob).version_id
        versions.write({
            'contract_date_start': '2021-10-10'
        })
        self.assertEqual(versions[0].contract_date_start, date(2021, 10, 10))
        self.assertEqual(versions[1].contract_date_start, date(2021, 10, 10))

    def test_multi_edit_multi_employees_all_contract(self):
        """
        Test the multi-edit when there is one version per employee, all with different contract
        """
        employee_john, employee_rob = self.env['hr.employee'].create([
            {
                'name': 'John Doe',
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
            },
            {
                'name': 'Rob Carter',
                'date_version': '2020-10-18',
                'contract_date_start': '2020-10-18',
            }
        ])
        versions = (employee_john | employee_rob).version_id
        versions |= employee_john.create_version({
            'date_version': '2021-08-01',
            'contract_date_start': '2020-01-01',
        })
        versions.write({
            'contract_date_start': '2021-10-10'
        })
        self.assertEqual(versions[0].contract_date_start, date(2021, 10, 10))
        self.assertEqual(versions[1].contract_date_start, date(2021, 10, 10))
        self.assertEqual(versions[2].contract_date_start, date(2021, 10, 10))

    def test_multi_edit_multi_employees_incompatible(self):
        """
        Test the multi-edit when there is one version per employee, one with incompatible dates
        """
        employee_john, employee_rob = self.env['hr.employee'].create([
            {
                'name': 'John Doe',
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
                'contract_date_end': '2020-10-10'
            },
            {
                'name': 'Rob Carter',
                'date_version': '2020-10-18',
                'contract_date_start': '2020-10-18',
            }
        ])
        versions = (employee_john | employee_rob).version_id
        versions |= employee_john.create_version({
            'date_version': '2021-08-01',
            'contract_date_start': '2021-08-01',
        })
        with self.assertRaises(ValidationError):
            versions.write({
                'contract_date_start': '2021-10-10'
            })

    def test_hr_version_fields_tracking(self):
        tracking_blacklist = {
            "__last_update",
            "active_employee",
            "activity_ids",
            "company_country_id",
            "contract_wage",
            "country_code",
            "create_date",
            "create_uid",
            "currency_id",
            "date_end",
            "date_start",
            "departure_description",
            "display_name",
            "id",
            "is_current",
            "is_flexible",
            "is_fully_flexible",
            "is_future",
            "is_in_contract",
            "is_past",
            "job_title",
            "last_modified_date",
            "last_modified_on",
            "last_modified_uid",
            "member_of_department",
            "message_follower_ids",
            "message_ids",
            "message_partner_ids",
            "rating_ids",
            "template_warning",
            "tz",
            "website_message_ids",
            "work_location_name",
            "work_location_type",
            "write_date",
            "write_uid",
        }

        hr_version_model = self.env['hr.version']
        fields_without_tracking = []

        for field_name, field in hr_version_model._fields.items():
            if field_name in tracking_blacklist:
                continue
            if field.compute and not field.inverse:
                continue
            if field.related:
                continue
            if hasattr(field, 'store') and field.store is False:
                continue
            if hasattr(field, 'tracking') and not field.tracking:
                fields_without_tracking.append(field_name)

        self.assertFalse(
            fields_without_tracking,
            f"The following hr.version fields should have tracking=True: {fields_without_tracking}",
        )

    def test_search_on_version_fields(self):
        Department = self.env['hr.department'].with_context(tracking_disable=True)
        rd_dep = Department.create({
            'name': 'Research and devlopment',
        })
        employee1, employee2 = employees = self.env['hr.employee'].create([
            {
                'contract_date_start': '2020-10-10',
                'wage': 3000,
                'name': 'Employee1',
                'hr_responsible_id': self.res_users_hr_manager.id,
                'department_id': rd_dep.id,
            },
            {
                'contract_date_start': '2022-10-10',
                'wage': 2000,
                'name': 'Employee2',
            },
        ])
        internal_user = mail_new_test_user(
            self.env,
            email='internal_user@example.com',
            login='internal_user',
            name='Internal User',
        )
        self.employee.department_id = rd_dep
        self.employee.user_id = internal_user

        HrEmployeePublic_with_internal_user = self.env['hr.employee.public'].with_user(internal_user)
        with self.assertRaises(AccessError, msg="Internal user should not be able to access to hr.employee model"):
            HrEmployeePublic_with_internal_user.search([
                ('employee_id.contract_date_start', '<', '2022-01-01'),
                ('id', 'in', employees.ids),
            ])
        with self.assertRaises(AccessError, msg="Internal user should not be able to access to hr.employee model"):
            HrEmployeePublic_with_internal_user.search([('employee_id.wage', '=', 2000), ('id', 'in', employees.ids)])
        with self.assertRaises(AccessError, msg="Internal user should not be able to access to hr.employee model"):
            HrEmployeePublic_with_internal_user.search([('employee_id.version_id.wage', '=', 2000), ('id', 'in', employees.ids)])
        self.assertEqual(
            HrEmployeePublic_with_internal_user.search([('name', '=', 'Employee2'), ('id', 'in', employees.ids)]),
            self.env['hr.employee.public'].browse(employee2.id),
        )
        self.assertEqual(
            HrEmployeePublic_with_internal_user.search([('member_of_department', '=', True), ('id', 'in', employees.ids)]),
            self.env['hr.employee.public'].browse(employee1.id),
        )

        HrEmployee_with_office_user = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        self.employee.user_id = self.res_users_hr_officer
        with self.assertRaises(AccessError, msg="HR Officer should not be able to access to 'payroll fields'"):
            HrEmployee_with_office_user.search([('contract_date_start', '<', '2022-01-01'), ('id', 'in', employees.ids)])
        with self.assertRaises(AccessError, msg="HR Officer should not be able to access to 'payroll fields'"):
            HrEmployee_with_office_user.search([('wage', '=', 2000), ('id', 'in', employees.ids)])
        with self.assertRaises(AccessError, msg="HR Officer should not be able to access to 'payroll fields'"):
            HrEmployee_with_office_user.search([('version_id.wage', '=', 2000), ('id', 'in', employees.ids)])
        self.assertEqual(HrEmployee_with_office_user.search([('name', '=', 'Employee1'), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_office_user.search([('hr_responsible_id', '=', self.res_users_hr_manager.id), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_office_user.search([('version_id.hr_responsible_id', '=', self.res_users_hr_manager.id), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_office_user.search([('member_of_department', '=', True), ('id', 'in', employees.ids)]), employee1)

        if payroll_group := self.env.ref('hr_payroll.group_hr_payroll_user', raise_if_not_found=False):
            self.res_users_hr_manager.group_ids += payroll_group
        HrEmployee_with_manager_user = self.env['hr.employee'].with_user(self.res_users_hr_manager)
        self.employee.user_id = self.res_users_hr_manager
        self.assertEqual(HrEmployee_with_manager_user.search([('contract_date_start', '<', '2022-01-01'), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_manager_user.search([('wage', '=', 2000), ('id', 'in', employees.ids)]), employee2)
        self.assertEqual(HrEmployee_with_manager_user.search([('version_id.wage', '=', 2000), ('id', 'in', employees.ids)]), employee2)
        self.assertEqual(HrEmployee_with_manager_user.search([('hr_responsible_id', '=', self.res_users_hr_manager.id), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_manager_user.search([('version_id.hr_responsible_id', '=', self.res_users_hr_manager.id), ('id', 'in', employees.ids)]), employee1)
        self.assertEqual(HrEmployee_with_manager_user.search([('member_of_department', '=', True), ('id', 'in', employees.ids)]), employee1)
