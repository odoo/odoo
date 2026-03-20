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
        generic_codes = [
            'WORK100',  # Attendance
            'OVERTIME',  # Overtime
            'OUT',  # Out of Contract
            'LEAVE100',  # Generic Time Off
            'LEAVE105',  # Compensatory Time Off
            'WORK110',  # Home Working
            'LEAVE90',  # Unpaid
            'LEAVE110',  # Sick Time Off
            'LEAVE120',  # Paid Time Off
        ]
        for module in self.env['ir.module.module'].search([('name', '=like', 'l10n____hr_payroll')]):
            country_code = module.name.split('_')[1]
            country = self.env.ref(f'base.{country_code}')
            for code in generic_codes:
                if not self.env['hr.work.entry.type'].search_count([('code', '=', code), ('country_id', '=', country.id)], limit=1):
                    raise ValidationError("Missing generic work entry redefinition with code %s for %s" % (code, country.name))
