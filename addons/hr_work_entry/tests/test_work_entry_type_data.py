# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.release import version_info
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestWorkEntryTypeData(TransactionCase):

    def test_ensure_work_entry_type_definition(self):
        # Make sure work entry types are defined in hr_work_entry in master (and not in other modules)
        # In the case this tests breaks during a forward port, move the work entry type definition
        # to hr_work_entry and make a upgrade script accordingly.
        if version_info[3] != 'alpha':
            return
        work_entry_types_xmlids = self.env['hr.work.entry.type'].search([('country_id', '!=', self.env.ref('base.ch').id)])._get_external_ids()
        invalid_xmlids = []
        for xmlids in work_entry_types_xmlids.values():
            for xmlid in xmlids:
                module = xmlid.split('.')[0]
                if module not in ['hr_work_entry', '__export__', '__custom__'] and not module.startswith('test_'):
                    invalid_xmlids.append(xmlid)
        if invalid_xmlids:
            raise ValidationError("Some work entry types are defined outside of module hr_work_entry.\n%s" % '\n'.join(invalid_xmlids))

    def test_ensure_global_work_entry_type_redifinition_by_country(self):
        generic_codes = {
            '002.00',  # Attendance
            '040.00',  # Overtime
            '000.00',  # Out of Contract
            'LEAVE100',  # Generic Time Off
            'LEAVE105',  # Compensatory Time Off
            '002.08',  # Home Working
            '158.00',  # Unpaid
            '013.00',  # Sick Time Off
            '016.00',  # Paid Time Off
            '006.00',  # Public Holiday
        }
        excluded_codes_per_country = {
            'us': {'040.00', '000.00', 'LEAVE100', 'LEAVE105'},
            'be': {'LEAVE100', 'LEAVE105'},
            'eg': {'013.00'},
        }
        for module in self.env['ir.module.module'].search([('name', '=like', 'l10n____hr_payroll')]):
            country_code = module.name.split('_')[1]
            country = self.env.ref(f'base.{country_code}')
            for code in generic_codes - excluded_codes_per_country.get(country_code, set()):
                if not self.env['hr.work.entry.type'].search_count([('code', '=', code), ('country_id', '=', country.id)], limit=1):
                    raise ValidationError("Missing generic work entry redefinition with code %s for %s" % (code, country.name))

    def test_work_entry_type_calendar_creation(self):
        """
        This is to test the implemention of automatically populating newly created
        work calendar with the default work calendar.
        """
        # the types are created on the country of the company, as the attendances of a
        # calendar can only use the types of the country of their company
        work_entries = self.env['hr.work.entry.type'].create([{
            'name': 'Test Work Entry Type %s' % day,
            'code': 'Test Work Entry Type %s' % day,
        } for day in range(5)])
        default_calendar = self.env['resource.calendar'].create({
            'name': '40 hours/week',
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'dayofweek': str(day), 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0, 'work_entry_type_id': work_entries[day].id})
                for day in range(5)
            ],
        })
        # Assigning the created calendar to the company resource calendar
        self.env.company.resource_calendar_id = default_calendar

        cloned_calendar = self.env['resource.calendar'].create({
            'name': 'Cloned 40hr/week',
        })
        self.assertEqual(
            len(default_calendar.attendance_ids),
            len(cloned_calendar.attendance_ids),
            f"Expected {len(default_calendar.attendance_ids)} days to be copied from the resource calendar but the duplicated calendar contains {len(cloned_calendar.attendance_ids)} days.")
        for day in range(len(cloned_calendar.attendance_ids)):
            self.assertEqual(
                cloned_calendar.attendance_ids[day].work_entry_type_id,
                default_calendar.attendance_ids[day].work_entry_type_id,
                f"{day} of copied calendar contains work entry '{cloned_calendar.attendance_ids[day].work_entry_type_id.name}' while it should contain work entry '{default_calendar.attendance_ids[day].work_entry_type_id.name}'")
