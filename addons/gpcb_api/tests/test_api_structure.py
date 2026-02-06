# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""Tests for gpcb_api module structure and endpoint definitions.

These tests validate the module layout, controller route definitions,
model fields, security rules, and view XML without requiring Odoo runtime.
"""

import ast
import csv
import os
import unittest
import xml.etree.ElementTree as ET

MODULE_PATH = 'addons/gpcb_api'


class TestModuleStructure(unittest.TestCase):
    """Validate the gpcb_api module directory layout."""

    def test_manifest_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__manifest__.py'))

    def test_init_exists(self):
        self.assertTrue(os.path.isfile(f'{MODULE_PATH}/__init__.py'))

    def test_controllers_dir_exists(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/controllers'))

    def test_models_dir_exists(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/models'))

    def test_views_dir_exists(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/views'))

    def test_security_dir_exists(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/security'))

    def test_tests_dir_exists(self):
        self.assertTrue(os.path.isdir(f'{MODULE_PATH}/tests'))


class TestManifest(unittest.TestCase):
    """Validate __manifest__.py content."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/__manifest__.py') as f:
            content = f.read()
        # Strip the leading comment line to get the dict
        cls.manifest = eval(content.split('{', 1)[0] + '{' + content.split('{', 1)[1])

    def test_name(self):
        self.assertEqual(self.manifest['name'], 'GPCB REST API')

    def test_depends(self):
        """Must depend on account, point_of_sale, and l10n_co_edi."""
        for dep in ('account', 'point_of_sale', 'l10n_co_edi'):
            self.assertIn(dep, self.manifest['depends'])

    def test_data_files(self):
        """Manifest data files must exist on disk."""
        for data_file in self.manifest.get('data', []):
            path = f'{MODULE_PATH}/{data_file}'
            self.assertTrue(os.path.isfile(path), f'{path} not found')


class TestControllerRoutes(unittest.TestCase):
    """Validate that all planned API routes are defined."""

    @classmethod
    def setUpClass(cls):
        cls.controllers = {}
        controller_dir = f'{MODULE_PATH}/controllers'
        for fname in os.listdir(controller_dir):
            if fname.startswith('api_') and fname.endswith('.py'):
                path = os.path.join(controller_dir, fname)
                with open(path) as f:
                    cls.controllers[fname] = f.read()

    def _assert_route(self, filename, route_suffix):
        """Assert that a route suffix exists in the given controller file.

        Routes use f-strings with API_PREFIX, so we check for the suffix
        portion after the API_PREFIX variable substitution.
        """
        content = self.controllers.get(filename, '')
        # The route suffix after API_PREFIX e.g. /invoices/<int:invoice_id>
        # appears in the f-string as: f'{API_PREFIX}/invoices/<int:invoice_id>'
        # Strip the /api/v1 prefix to get what follows in the f-string
        suffix = route_suffix.replace('/api/v1', '')
        self.assertIn(suffix, content,
                       f'Route suffix {suffix} missing from {filename}')

    # Invoice endpoints
    def test_invoice_create_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices')

    def test_invoice_get_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices/<int:invoice_id>')

    def test_invoice_confirm_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices/<int:invoice_id>/confirm')

    def test_invoice_cancel_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices/<int:invoice_id>/cancel')

    def test_invoice_pdf_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices/<int:invoice_id>/pdf')

    def test_invoice_xml_route(self):
        self._assert_route('api_invoice.py', '/api/v1/invoices/<int:invoice_id>/xml')

    # Partner endpoints
    def test_partner_list_route(self):
        self._assert_route('api_partner.py', '/api/v1/partners')

    def test_partner_get_route(self):
        self._assert_route('api_partner.py', '/api/v1/partners/<int:partner_id>')

    def test_partner_create_route(self):
        content = self.controllers.get('api_partner.py', '')
        self.assertIn("methods=['POST']", content)

    def test_partner_update_route(self):
        content = self.controllers.get('api_partner.py', '')
        self.assertIn("methods=['PATCH']", content)

    # Product endpoints
    def test_product_list_route(self):
        self._assert_route('api_product.py', '/api/v1/products')

    def test_product_get_route(self):
        self._assert_route('api_product.py', '/api/v1/products/<int:product_id>')

    # Tax endpoint
    def test_tax_compute_route(self):
        self._assert_route('api_tax.py', '/api/v1/tax/compute')

    # POS session endpoints
    def test_pos_session_open_route(self):
        self._assert_route('api_pos_session.py', '/api/v1/pos/sessions/open')

    def test_pos_session_close_route(self):
        self._assert_route('api_pos_session.py', '/api/v1/pos/sessions/<int:session_id>/close')

    def test_pos_session_summary_route(self):
        self._assert_route('api_pos_session.py', '/api/v1/pos/sessions/<int:session_id>/summary')

    # Report endpoints
    def test_report_dashboard_route(self):
        self._assert_route('api_report.py', '/api/v1/reports/dashboard')

    def test_report_dian_status_route(self):
        self._assert_route('api_report.py', '/api/v1/reports/dian-status')


class TestControllerAuth(unittest.TestCase):
    """Validate that all routes use bearer authentication."""

    @classmethod
    def setUpClass(cls):
        cls.all_content = ''
        controller_dir = f'{MODULE_PATH}/controllers'
        for fname in os.listdir(controller_dir):
            if fname.startswith('api_') and fname.endswith('.py'):
                with open(os.path.join(controller_dir, fname)) as f:
                    cls.all_content += f.read() + '\n'

    def test_all_routes_use_bearer_auth(self):
        """Every @http.route must use auth='bearer'."""
        # Count route decorators and bearer auth declarations
        import re
        routes = re.findall(r"@http\.route\(", self.all_content)
        bearer_auths = re.findall(r"auth='bearer'", self.all_content)
        self.assertEqual(len(routes), len(bearer_auths),
                         'Not all routes use bearer authentication')

    def test_all_routes_disable_csrf(self):
        """All API routes should disable CSRF."""
        import re
        routes = re.findall(r"@http\.route\(", self.all_content)
        csrf_false = re.findall(r"csrf=False", self.all_content)
        self.assertEqual(len(routes), len(csrf_false),
                         'Not all routes disable CSRF')


class TestApiLogModel(unittest.TestCase):
    """Validate the API log model."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/models/gpcb_api_log.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'gpcb.api.log'", self.content)

    def test_required_fields(self):
        for field in ('endpoint', 'method', 'user_id', 'request_body',
                      'response_body', 'status_code', 'duration_ms',
                      'ip_address', 'error_message'):
            self.assertIn(field, self.content, f'Field {field} missing')

    def test_gc_method(self):
        """Must have autovacuum garbage collection."""
        self.assertIn('_gc_old_logs', self.content)
        self.assertIn('autovacuum', self.content)


class TestSecurityRules(unittest.TestCase):
    """Validate security access CSV."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/security/ir.model.access.csv') as f:
            cls.rows = list(csv.DictReader(f))

    def test_api_log_access_exists(self):
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_gpcb_api_log', model_ids)

    def test_admin_has_full_access(self):
        admin_rules = [r for r in self.rows if 'admin' in r['id']]
        self.assertTrue(len(admin_rules) >= 1)
        for rule in admin_rules:
            self.assertEqual(rule['perm_read'], '1')
            self.assertEqual(rule['perm_write'], '1')


class TestViewsXml(unittest.TestCase):
    """Validate view XML files."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(f'{MODULE_PATH}/views/gpcb_api_log_views.xml')
        cls.root = cls.tree.getroot()

    def test_list_view_exists(self):
        ids = [r.get('id') for r in self.root.findall('record')]
        self.assertIn('gpcb_api_log_list', ids)

    def test_form_view_exists(self):
        ids = [r.get('id') for r in self.root.findall('record')]
        self.assertIn('gpcb_api_log_form', ids)

    def test_action_exists(self):
        ids = [r.get('id') for r in self.root.findall('record')]
        self.assertIn('action_gpcb_api_log', ids)

    def test_menu_exists(self):
        menus = self.root.findall('menuitem')
        self.assertTrue(len(menus) >= 1)


class TestInvoiceController(unittest.TestCase):
    """Validate invoice controller has key helper methods."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_invoice.py') as f:
            cls.content = f.read()

    def test_resolve_partner(self):
        self.assertIn('_resolve_partner', self.content)

    def test_resolve_journal(self):
        self.assertIn('_resolve_journal', self.content)

    def test_serialize_invoice(self):
        self.assertIn('_serialize_invoice', self.content)

    def test_build_invoice_line(self):
        self.assertIn('_build_invoice_line', self.content)

    def test_vet_lab_fields_support(self):
        """Invoice controller should handle vet/lab domain fields."""
        self.assertIn('animal_id', self.content)
        self.assertIn('animal_species', self.content)
        self.assertIn('x_vet_', self.content)

    def test_dian_fields_in_serialization(self):
        """Serialized invoice should include DIAN fields."""
        self.assertIn('dian_state', self.content)
        self.assertIn('cufe', self.content)
        self.assertIn('l10n_co_edi_state', self.content)


class TestTaxController(unittest.TestCase):
    """Validate tax computation controller."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_tax.py') as f:
            cls.content = f.read()

    def test_compute_all_used(self):
        """Must use Odoo's compute_all for accurate tax calculation."""
        self.assertIn('compute_all', self.content)

    def test_fiscal_position_applied(self):
        """Must apply fiscal position for partner-specific tax mapping."""
        self.assertIn('fiscal_position', self.content)


class TestReportController(unittest.TestCase):
    """Validate report controller."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_report.py') as f:
            cls.content = f.read()

    def test_dashboard_returns_key_metrics(self):
        """Dashboard should return revenue, expenses, IVA, DIAN stats."""
        for metric in ('revenue', 'expenses', 'iva_collected', 'iva_paid',
                       'receivable', 'payable', 'dian'):
            self.assertIn(metric, self.content)


if __name__ == '__main__':
    unittest.main()
