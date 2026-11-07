# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('post_install', '-at_install')
class TestHrContractPdfWizard(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the wage is restricted to the payroll users when the payroll is installed
        if payroll_group := cls.env.ref('hr_payroll.group_hr_payroll_user', raise_if_not_found=False):
            cls.res_users_hr_manager.group_ids |= payroll_group
        cls.job = cls.env['hr.job'].create({'name': 'Developer'})
        # first contract, two versions
        cls.contract_employee = cls.env['hr.employee'].create({
            'name': 'Jane Doe',
            'legal_name': 'Jane Doe',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'contract_date_end': date(2025, 12, 31),
            'wage': 3000,
        })
        cls.version_1 = cls.contract_employee.version_id
        cls.version_2 = cls.contract_employee.create_version({'date_version': date(2025, 6, 1)})
        # second contract
        cls.version_3 = cls.contract_employee.create_contract(date(2026, 1, 1))

    def _create_wizard(self, version, **vals):
        return self.env['hr.contract.pdf.wizard'].with_user(self.res_users_hr_manager).create({
            'version_id': version.id,
            **vals,
        })

    def test_generate_contract(self):
        wizard = self._create_wizard(self.version_1, wage=3500, job_id=self.job.id, legal_name='Jane Smith')
        self.assertEqual(wizard.contract_date_start, date(2025, 1, 1))
        self.assertEqual(wizard.contract_date_end, date(2025, 12, 31))

        wizard.action_generate_pdf()

        self.assertEqual(self.version_1.wage, 3500)
        self.assertEqual(self.version_1.job_id, self.job)
        self.assertEqual(self.contract_employee.legal_name, 'Jane Smith')
        self.assertTrue(self.version_1.contract_file)
        self.assertIn(b'Jane Smith', self.version_1.contract_file.content)
        self.assertFalse(self.version_2.contract_file, "The later versions are only updated on request")
        self.assertEqual(self.version_2.wage, 3000)

    def test_generate_contract_update_future_versions(self):
        wizard = self._create_wizard(self.version_1, wage=3500)
        changes_to_display = wizard.get_future_version_changes()
        self.assertIn('(Wage)', changes_to_display)
        self.assertIn('(Contract File)', changes_to_display)

        wizard.with_context(hr_contract_update_future_versions=True).action_generate_pdf()

        self.assertEqual((self.version_1 | self.version_2).mapped('wage'), [3500, 3500])
        self.assertTrue(self.version_2.contract_file)
        self.assertEqual(self.version_3.wage, 3000, "The versions of another contract are not updated")
        self.assertFalse(self.version_3.contract_file, "The versions of another contract are not updated")

    def test_no_future_version_changes_on_last_version(self):
        wizard = self._create_wizard(self.version_3, wage=3500)
        self.assertEqual(wizard.get_future_version_changes(), {})

    def test_contract_file_not_copied_to_another_contract(self):
        self.version_3.write({
            'contract_file': BinaryBytes(b'contract'),
            'contract_date_end': date(2026, 12, 31),
        })
        same_contract_version = self.contract_employee.create_version({'date_version': date(2026, 6, 1)})
        self.assertEqual(same_contract_version.contract_file.content, b'contract')
        new_contract_version = self.contract_employee.create_contract(date(2027, 1, 1))
        self.assertFalse(new_contract_version.contract_file)

    def test_install_contract_lang(self):
        lang = self.env['res.lang'].with_context(active_test=False).search([('active', '=', False)], limit=1)
        if not lang:
            self.skipTest("No inactive language to install")
        wizard = self._create_wizard(self.version_1, contract_lang_id=lang.id)
        with patch.object(self.registry['ir.module.module'], '_update_translations') as update_translations:
            wizard.action_generate_pdf()
        self.assertTrue(lang.active)
        update_translations.assert_called_once_with([lang.code])
        self.assertTrue(self.version_1.contract_file)
