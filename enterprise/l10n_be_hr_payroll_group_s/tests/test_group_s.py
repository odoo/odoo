# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import RedirectWarning, ValidationError


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestHrContractGroupSCode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.belgium = cls.env.ref('base.be')
        cls.company = cls.env['res.company'].create({
            'name': 'Test Belgium Company',
            'country_id': cls.belgium.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
            'wage': 3000,
            'group_s_code': '123456',
            'country_code': 'BE',
            'state': 'open',
        })

    def test_invalid_group_s_code_length(self):
        """Test invalid Group S code length (Belgium)"""
        with self.assertRaises(ValidationError):
            self.contract.write({'group_s_code': '12345'})

    def test_unique_group_s_code(self):
        """Test Group S code uniqueness within the same company"""
        with self.assertRaises(ValidationError):
            self.env['hr.contract'].create({
                'name': 'Duplicate Group S Code Contract',
                'employee_id': self.employee.id,
                'company_id': self.company.id,
                'wage': 3000,
                'group_s_code': '123456',
                'country_code': 'BE',
                'state': 'open',
            })

    def test_group_s_code_in_different_company(self):
        """Test the same Group S code in a different company"""
        other_company = self.env['res.company'].create({
            'name': 'Other Company',
            'country_id': self.belgium.id,
        })
        other_contract = self.env['hr.contract'].create({
            'name': 'Contract in Other Company',
            'employee_id': self.employee.id,
            'company_id': other_company.id,
            'wage': 2000,
            'group_s_code': '123456',
            'country_code': 'BE',
            'state': 'open',
        })
        self.assertEqual(other_contract.group_s_code, '123456', "Group S code should be valid in a different company.")

    def test_export_to_group_s_with_no_group_s_code_in_company(self):
        """Test export to Group S with no Group S code in the company"""
        with self.assertRaises(RedirectWarning):
            self.env['l10n.be.hr.payroll.export.group.s'].with_company(
                self.company.id).create({}).action_export_file()
