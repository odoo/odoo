# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""Tests for endpoint response format consistency and API contract.

These tests validate the structure and consistency of endpoint helper
methods and serialization patterns without requiring Odoo runtime.
"""

import ast
import os
import re
import unittest

MODULE_PATH = 'addons/gpcb_api'


class TestEndpointResponseConsistency(unittest.TestCase):
    """All endpoints must return consistent JSON response format."""

    @classmethod
    def setUpClass(cls):
        cls.controller_contents = {}
        controller_dir = f'{MODULE_PATH}/controllers'
        for fname in os.listdir(controller_dir):
            if fname.startswith('api_') and fname.endswith('.py'):
                with open(os.path.join(controller_dir, fname)) as f:
                    cls.controller_contents[fname] = f.read()

    def test_success_responses_have_status_field(self):
        """All success responses must include 'status': 'success'."""
        for fname, content in self.controller_contents.items():
            self.assertIn("'status': 'success'", content,
                          f'{fname} missing success status in responses')

    def test_error_responses_have_status_field(self):
        """Controllers with write operations must include 'status': 'error'."""
        # Read-only controllers (api_report) may not have error responses
        write_controllers = {
            k: v for k, v in self.controller_contents.items()
            if k != 'api_report.py'
        }
        for fname, content in write_controllers.items():
            self.assertIn("'status': 'error'", content,
                          f'{fname} missing error status in responses')

    def test_error_responses_have_message(self):
        """Controllers with write operations must include a message field."""
        write_controllers = {
            k: v for k, v in self.controller_contents.items()
            if k != 'api_report.py'
        }
        for fname, content in write_controllers.items():
            self.assertIn("'message':", content,
                          f'{fname} missing message in error responses')

    def test_all_use_make_json_response(self):
        """All endpoints must use request.make_json_response."""
        for fname, content in self.controller_contents.items():
            self.assertIn('make_json_response', content,
                          f'{fname} not using make_json_response')


class TestPaginationSupport(unittest.TestCase):
    """List endpoints must support pagination."""

    @classmethod
    def setUpClass(cls):
        cls.list_controllers = {}
        controller_dir = f'{MODULE_PATH}/controllers'
        for fname in ('api_invoice.py', 'api_partner.py', 'api_product.py'):
            path = os.path.join(controller_dir, fname)
            if os.path.isfile(path):
                with open(path) as f:
                    cls.list_controllers[fname] = f.read()

    def test_limit_parameter(self):
        """List endpoints must accept limit parameter."""
        for fname, content in self.list_controllers.items():
            self.assertIn('limit', content,
                          f'{fname} missing limit parameter')

    def test_offset_parameter(self):
        """List endpoints must accept offset parameter."""
        for fname, content in self.list_controllers.items():
            self.assertIn('offset', content,
                          f'{fname} missing offset parameter')

    def test_total_in_response(self):
        """List endpoints must return total count."""
        for fname, content in self.list_controllers.items():
            self.assertIn("'total'", content,
                          f'{fname} missing total in response')

    def test_max_limit_enforced(self):
        """List endpoints must enforce a maximum limit."""
        for fname, content in self.list_controllers.items():
            self.assertIn('200', content,
                          f'{fname} should enforce max limit of 200')


class TestInvoiceSerializationFields(unittest.TestCase):
    """Invoice serialization must include required fields for POS and mobile."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_invoice.py') as f:
            cls.content = f.read()

    def test_core_fields(self):
        """Must serialize core invoice fields."""
        for field in ('id', 'name', 'state', 'move_type', 'amount_total',
                      'amount_untaxed', 'amount_tax', 'amount_residual',
                      'currency', 'partner_name'):
            self.assertIn(f"'{field}'", self.content,
                          f'Field {field} missing from invoice serialization')

    def test_dian_fields(self):
        """Must serialize DIAN electronic invoicing fields."""
        for field in ('dian_state', 'cufe', 'has_xml'):
            self.assertIn(f"'{field}'", self.content,
                          f'DIAN field {field} missing from invoice serialization')

    def test_line_fields(self):
        """Must serialize invoice line details."""
        for field in ('product_code', 'description', 'quantity',
                      'price_unit', 'price_subtotal'):
            self.assertIn(f"'{field}'", self.content,
                          f'Line field {field} missing from serialization')


class TestPartnerSerializationFields(unittest.TestCase):
    """Partner serialization must include Colombian fiscal fields."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_partner.py') as f:
            cls.content = f.read()

    def test_core_fields(self):
        for field in ('id', 'name', 'vat', 'email', 'phone'):
            self.assertIn(f"'{field}'", self.content)

    def test_colombian_fiscal_fields(self):
        """Must serialize Colombian fiscal classification."""
        for field in ('tax_regime', 'gran_contribuyente', 'fiscal_responsibilities'):
            self.assertIn(f"'{field}'", self.content,
                          f'Colombian field {field} missing from partner serialization')

    def test_nit_duplicate_check(self):
        """Partner creation must check for duplicate NITs."""
        self.assertIn('already exists', self.content)


class TestProductSerializationFields(unittest.TestCase):
    """Product serialization must include tax defaults."""

    @classmethod
    def setUpClass(cls):
        with open(f'{MODULE_PATH}/controllers/api_product.py') as f:
            cls.content = f.read()

    def test_core_fields(self):
        for field in ('id', 'name', 'code', 'list_price'):
            self.assertIn(f"'{field}'", self.content)

    def test_tax_fields(self):
        """Must include default taxes for automatic assignment."""
        self.assertIn('taxes_id', self.content)
        self.assertIn('supplier_taxes_id', self.content)

    def test_barcode_search(self):
        """Must support barcode/SKU lookup."""
        self.assertIn('barcode', self.content)


class TestControllerModuleIntegration(unittest.TestCase):
    """Validate all controllers are imported."""

    def test_controllers_init(self):
        with open(f'{MODULE_PATH}/controllers/__init__.py') as f:
            content = f.read()
        for module in ('api_invoice', 'api_partner', 'api_product',
                       'api_tax', 'api_pos_session', 'api_report'):
            self.assertIn(module, content,
                          f'Controller {module} not imported')

    def test_models_init(self):
        with open(f'{MODULE_PATH}/models/__init__.py') as f:
            content = f.read()
        self.assertIn('gpcb_api_log', content)


if __name__ == '__main__':
    unittest.main()
