# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""Tests for payroll EDI module structure, models, views, and security."""

import ast
import csv
import os
import unittest
import xml.etree.ElementTree as ET

MODULE_PATH = 'addons/l10n_co_payroll_edi'


class TestModuleStructure(unittest.TestCase):
    """Validate module directory layout."""

    def test_manifest_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__manifest__.py'))

    def test_init_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__init__.py'))

    def test_models_dir(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/models'))

    def test_wizard_dir(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/wizard'))

    def test_views_dir(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/views'))


class TestManifest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/__manifest__.py') as f:
            content = f.read()
        cls.manifest = eval(content.split('{', 1)[0] + '{' + content.split('{', 1)[1])

    def test_depends(self):
        for dep in ('hr', 'account', 'l10n_co_edi'):
            self.assertIn(dep, self.manifest['depends'])

    def test_data_files_exist(self):
        for data_file in self.manifest.get('data', []):
            path = f'{MODULE_PATH}/{data_file}'
            self.assertTrue(os.path.isfile(path), f'{path} not found')


class TestPayrollDocumentModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/l10n_co_payroll_document.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'l10n_co.payroll.document'", self.content)

    def test_inherits_mail_thread(self):
        self.assertIn("'mail.thread'", self.content)

    def test_required_fields(self):
        for field in ('employee_id', 'period_start', 'period_end',
                      'settlement_date', 'document_number', 'document_type',
                      'state', 'cune', 'xml_file', 'move_id'):
            self.assertIn(field, self.content, f'Field {field} missing')

    def test_document_types(self):
        for dt in ('nomina', 'ajuste', 'nota'):
            self.assertIn(f"'{dt}'", self.content)

    def test_state_machine(self):
        for state in ('draft', 'confirmed', 'sent', 'validated', 'rejected'):
            self.assertIn(f"'{state}'", self.content)

    def test_totals_computed(self):
        self.assertIn('total_earnings', self.content)
        self.assertIn('total_deductions', self.content)
        self.assertIn('net_pay', self.content)

    def test_earning_deduction_provision_lines(self):
        self.assertIn('earning_ids', self.content)
        self.assertIn('deduction_ids', self.content)
        self.assertIn('provision_ids', self.content)

    def test_xml_generation(self):
        self.assertIn('_build_payroll_xml', self.content)
        self.assertIn('NominaIndividual', self.content)

    def test_dian_submission(self):
        self.assertIn('action_send_to_dian', self.content)

    def test_accounting_entry(self):
        self.assertIn('action_create_accounting_entry', self.content)
        self.assertIn('_build_journal_entry_lines', self.content)

    def test_labor_constants(self):
        """Must define SMMLV and transport subsidy constants."""
        self.assertIn('SMMLV_2026', self.content)
        self.assertIn('TRANSPORT_SUBSIDY_2026', self.content)


class TestPayrollLineModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/l10n_co_payroll_line.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'l10n_co.payroll.document.line'", self.content)

    def test_required_fields(self):
        for field in ('document_id', 'line_type', 'concept', 'amount',
                      'rate', 'quantity', 'account_id', 'concept_code'):
            self.assertIn(field, self.content, f'Field {field} missing')

    def test_line_types(self):
        for lt in ('earning', 'deduction', 'provision'):
            self.assertIn(f"'{lt}'", self.content)


class TestCompanyFields(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/res_company.py') as f:
            cls.content = f.read()

    def test_payroll_enabled_field(self):
        self.assertIn('l10n_co_payroll_edi_enabled', self.content)

    def test_employer_type_field(self):
        self.assertIn('l10n_co_payroll_edi_employer_type', self.content)


class TestImportWizard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/wizard/payroll_import_wizard.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'l10n_co.payroll.import.wizard'", self.content)

    def test_csv_import(self):
        self.assertIn('csv_file', self.content)
        self.assertIn('action_import', self.content)
        self.assertIn('csv.DictReader', self.content)

    def test_earning_field_mapping(self):
        """Wizard must map common CSV columns to earning concepts."""
        for field in ('salary', 'transport', 'overtime_hed', 'commission'):
            self.assertIn(f"'{field}'", self.content)


class TestSendWizard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/wizard/payroll_send_wizard.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'l10n_co.payroll.send.wizard'", self.content)

    def test_batch_send(self):
        self.assertIn('action_send', self.content)


class TestSecurityRules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/security/ir.model.access.csv') as f:
            cls.rows = list(csv.DictReader(f))

    def test_document_access(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_payroll_document', model_ids)

    def test_line_access(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_payroll_document_line', model_ids)

    def test_wizard_access(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_payroll_import_wizard', model_ids)
        self.assertIn('model_l10n_co_payroll_send_wizard', model_ids)


class TestViewsXml(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/views/l10n_co_payroll_document_views.xml')
        cls.root = cls.tree.getroot()
        cls.records = cls.root.findall('record')

    def test_list_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_payroll_document_list', ids)

    def test_form_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_payroll_document_form', ids)

    def test_import_wizard_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_payroll_import_wizard_form', ids)

    def test_send_wizard_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_payroll_send_wizard_form', ids)

    def test_action(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('action_l10n_co_payroll_document', ids)

    def test_menus(self):
        menus = self.root.findall('menuitem')
        menu_ids = [m.get('id') for m in menus]
        self.assertIn('menu_l10n_co_payroll_edi', menu_ids)
        self.assertIn('menu_l10n_co_payroll_documents', menu_ids)
        self.assertIn('menu_l10n_co_payroll_import', menu_ids)
        self.assertIn('menu_l10n_co_payroll_send', menu_ids)


class TestDataXml(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/data/l10n_co_payroll_edi_data.xml')
        cls.root = cls.tree.getroot()

    def test_sequence_defined(self):
        records = self.root.findall('record')
        ids = [r.get('id') for r in records]
        self.assertIn('sequence_payroll_document', ids)


class TestModuleImports(unittest.TestCase):

    def test_models_init(self):
        with open(f'{MODULE_PATH}/models/__init__.py') as f:
            content = f.read()
        for mod in ('l10n_co_payroll_document', 'l10n_co_payroll_line',
                     'l10n_co_payroll_cune', 'res_company'):
            self.assertIn(mod, content)

    def test_wizard_init(self):
        with open(f'{MODULE_PATH}/wizard/__init__.py') as f:
            content = f.read()
        self.assertIn('payroll_import_wizard', content)
        self.assertIn('payroll_send_wizard', content)


if __name__ == '__main__':
    unittest.main()
