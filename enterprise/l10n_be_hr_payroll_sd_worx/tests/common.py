# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_be_hr_payroll.tests.common import TestPayrollCommon


class TestSdworxExportCommon(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.belgian_company.write({
            'sdworx_code': '1234567'
        })

        cls.employee_georges.sdworx_code = '0000001'
        cls.employee_john.sdworx_code = '0000002'
        cls.employee_a.sdworx_code = '0000003'
        cls.employee_withholding_taxes.sdworx_code = '0000004'
        cls.employee_test.sdworx_code = '0000005'
        cls.employee_with_attestation.sdworx_code = '0000006'

        cls.gto_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'GTO Work Entry',
            'code': 'LEAVE11',
            'sdworx_code': '7010',
        })

        cls.pto_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'PTO Work Entry',
            'code': 'LEAVE12',
            'sdworx_code': 'T010',
        })
