# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""Tests for gpcb_report_scheduler module structure and model definitions."""

import ast
import csv
import os
import unittest
import xml.etree.ElementTree as ET

MODULE_PATH = 'addons/gpcb_report_scheduler'


class TestModuleStructure(unittest.TestCase):
    """Validate the module directory layout."""

    def test_manifest_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__manifest__.py'))

    def test_init_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__init__.py'))

    def test_models_init(self):
        with open(f'{MODULE_PATH}/models/__init__.py') as f:
            content = f.read()
        self.assertIn('report_schedule', content)
        self.assertIn('report_schedule_run', content)


class TestManifest(unittest.TestCase):
    """Validate __manifest__.py content."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/__manifest__.py') as f:
            content = f.read()
        cls.manifest = eval(content.split('{', 1)[0] + '{' + content.split('{', 1)[1])

    def test_depends(self):
        for dep in ('account', 'mail', 'l10n_co_edi'):
            self.assertIn(dep, self.manifest['depends'])

    def test_data_files_exist(self):
        for data_file in self.manifest.get('data', []):
            path = f'{MODULE_PATH}/{data_file}'
            self.assertTrue(os.path.isfile(path), f'{path} not found')


class TestReportScheduleModel(unittest.TestCase):
    """Validate report schedule model."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/report_schedule.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'gpcb.report.schedule'", self.content)

    def test_inherits_mail_thread(self):
        self.assertIn("'mail.thread'", self.content)

    def test_report_types_defined(self):
        """All 9 report types must be in the selection."""
        for rt in ('iva_300', 'withholding_350', 'ica', 'income_tax',
                    'withholding_cert', 'exogenous', 'balance_sheet',
                    'profit_loss', 'trial_balance'):
            self.assertIn(f"'{rt}'", self.content,
                          f'Report type {rt} missing')

    def test_frequency_selection(self):
        for freq in ('monthly', 'bimonthly', 'quarterly', 'annual'):
            self.assertIn(f"'{freq}'", self.content)

    def test_required_fields(self):
        for field in ('name', 'report_type', 'frequency', 'day_of_month',
                      'lead_days', 'auto_send', 'state', 'recipient_ids',
                      'run_ids', 'last_run_date', 'next_run_date'):
            self.assertIn(field, self.content, f'Field {field} missing')

    def test_cron_method(self):
        self.assertIn('_cron_generate_reports', self.content)

    def test_execute_schedule_method(self):
        self.assertIn('_execute_schedule', self.content)

    def test_get_report_period(self):
        self.assertIn('_get_report_period', self.content)

    def test_get_next_run_date(self):
        self.assertIn('_get_next_run_date', self.content)

    def test_action_run_now(self):
        self.assertIn('action_run_now', self.content)

    def test_action_pause_activate(self):
        self.assertIn('action_pause', self.content)
        self.assertIn('action_activate', self.content)


class TestReportScheduleRunModel(unittest.TestCase):
    """Validate report schedule run model."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/report_schedule_run.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'gpcb.report.schedule.run'", self.content)

    def test_required_fields(self):
        for field in ('schedule_id', 'date_from', 'date_to', 'state',
                      'report_data', 'pdf_file', 'notes', 'error_message',
                      'sent_date'):
            self.assertIn(field, self.content, f'Field {field} missing')

    def test_state_machine(self):
        for state in ('generated', 'review', 'approved', 'sent', 'failed'):
            self.assertIn(f"'{state}'", self.content)

    def test_generate_method(self):
        self.assertIn('_generate_report_content', self.content)

    def test_tax_report_generator(self):
        self.assertIn('_generate_tax_report_data', self.content)

    def test_withholding_cert_generator(self):
        self.assertIn('_generate_withholding_cert_summary', self.content)

    def test_exogenous_generator(self):
        self.assertIn('_generate_exogenous_summary', self.content)

    def test_financial_report_generator(self):
        self.assertIn('_generate_financial_report_data', self.content)

    def test_send_to_recipients(self):
        self.assertIn('_send_to_recipients', self.content)

    def test_action_approve(self):
        self.assertIn('action_approve', self.content)

    def test_action_send(self):
        self.assertIn('action_send', self.content)

    def test_uses_mail_mail(self):
        """Must use Odoo's mail.mail for email delivery."""
        self.assertIn("'mail.mail'", self.content)


class TestCronData(unittest.TestCase):
    """Validate cron job configuration."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/data/ir_cron_data.xml')
        cls.root = cls.tree.getroot()

    def test_cron_record_exists(self):
        records = self.root.findall('record')
        cron_ids = [r.get('id') for r in records]
        self.assertIn('ir_cron_report_scheduler', cron_ids)

    def test_cron_calls_correct_method(self):
        record = self.root.find('.//record[@id="ir_cron_report_scheduler"]')
        code_field = record.find('.//field[@name="code"]')
        self.assertIn('_cron_generate_reports', code_field.text)

    def test_cron_runs_daily(self):
        record = self.root.find('.//record[@id="ir_cron_report_scheduler"]')
        interval = record.find('.//field[@name="interval_type"]')
        self.assertEqual(interval.text, 'days')


class TestScheduleData(unittest.TestCase):
    """Validate pre-configured Colombian schedules."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/data/report_schedule_data.xml')
        cls.root = cls.tree.getroot()
        cls.records = cls.root.findall('record')

    def test_at_least_6_schedules(self):
        """Must have at least 6 pre-configured schedules."""
        self.assertGreaterEqual(len(self.records), 6)

    def test_iva_schedule_exists(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('schedule_iva_300', ids)

    def test_withholding_schedule_exists(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('schedule_withholding_350', ids)

    def test_exogenous_schedule_exists(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('schedule_exogenous', ids)

    def test_all_start_paused(self):
        """Pre-configured schedules should start paused."""
        for record in self.records:
            state_field = record.find('.//field[@name="state"]')
            if state_field is not None:
                self.assertEqual(state_field.text, 'paused',
                                 f'{record.get("id")} should start paused')


class TestSecurityRules(unittest.TestCase):
    """Validate security access CSV."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/security/ir.model.access.csv') as f:
            cls.rows = list(csv.DictReader(f))

    def test_schedule_access_exists(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_gpcb_report_schedule', model_ids)

    def test_run_access_exists(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_gpcb_report_schedule_run', model_ids)

    def test_user_read_only(self):
        user_rules = [r for r in self.rows if 'user' in r['id']]
        for rule in user_rules:
            self.assertEqual(rule['perm_read'], '1')
            self.assertEqual(rule['perm_write'], '0')


class TestViewsXml(unittest.TestCase):
    """Validate view XML files."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/views/report_schedule_views.xml')
        cls.root = cls.tree.getroot()
        cls.records = cls.root.findall('record')

    def test_schedule_list_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('gpcb_report_schedule_list', ids)

    def test_schedule_form_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('gpcb_report_schedule_form', ids)

    def test_run_list_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('gpcb_report_schedule_run_list', ids)

    def test_run_form_view(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('gpcb_report_schedule_run_form', ids)

    def test_actions_defined(self):
        ids = [r.get('id') for r in self.records]
        self.assertIn('action_gpcb_report_schedule', ids)
        self.assertIn('action_gpcb_report_schedule_run', ids)

    def test_menus_defined(self):
        menus = self.root.findall('menuitem')
        menu_ids = [m.get('id') for m in menus]
        self.assertIn('menu_gpcb_report_scheduler', menu_ids)


if __name__ == '__main__':
    unittest.main()
