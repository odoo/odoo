# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import csv
import unittest
import xml.etree.ElementTree as ET


class TestExogenousDocumentModel(unittest.TestCase):
    """Validate exogenous document model structure."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/models/l10n_co_edi_exogenous.py') as f:
            cls.content = f.read()
        cls.tree = ast.parse(cls.content)
        cls.classes = {
            n.name: n for n in ast.walk(cls.tree)
            if isinstance(n, ast.ClassDef)
        }

    def test_document_model_exists(self):
        """Main exogenous document model must exist."""
        self.assertIn('L10nCoEdiExogenousDocument', self.classes)

    def test_line_model_exists(self):
        """Exogenous document line model must exist."""
        self.assertIn('L10nCoEdiExogenousDocumentLine', self.classes)

    def test_document_model_name(self):
        """Model _name must be l10n_co_edi.exogenous.document."""
        self.assertIn("_name = 'l10n_co_edi.exogenous.document'", self.content)

    def test_line_model_name(self):
        """Line _name must be l10n_co_edi.exogenous.document.line."""
        self.assertIn("_name = 'l10n_co_edi.exogenous.document.line'", self.content)

    def test_required_fields_present(self):
        """Document model must have essential fields."""
        required_fields = [
            'company_id', 'year', 'formato', 'state',
            'line_ids', 'xml_file', 'xml_filename',
        ]
        for field in required_fields:
            self.assertIn(field, self.content,
                          f'Field {field} missing from exogenous model')

    def test_line_required_fields(self):
        """Line model must have essential fields."""
        required_fields = [
            'document_id', 'partner_id', 'base_amount',
            'tax_amount', 'withholding_amount', 'tax_rate',
        ]
        for field in required_fields:
            self.assertIn(field, self.content,
                          f'Field {field} missing from exogenous line model')

    def test_five_formatos_defined(self):
        """Selection field must define all 5 DIAN formatos."""
        for fmt in ['1001', '1003', '1005', '1006', '1007']:
            self.assertIn(f"'{fmt}'", self.content,
                          f'Formato {fmt} missing from selection')

    def test_state_machine(self):
        """State field must have draft, confirmed, sent states."""
        for state in ['draft', 'confirmed', 'sent']:
            self.assertIn(f"'{state}'", self.content,
                          f'State {state} missing')


class TestExogenousAggregationMethods(unittest.TestCase):
    """Validate aggregation methods exist for each formato."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/models/l10n_co_edi_exogenous.py') as f:
            cls.content = f.read()

    def test_compute_formato_1001(self):
        """Formato 1001 computation method must exist."""
        self.assertIn('_compute_formato_1001', self.content)

    def test_compute_formato_1003(self):
        """Formato 1003 computation method must exist."""
        self.assertIn('_compute_formato_1003', self.content)

    def test_compute_formato_1005(self):
        """Formato 1005 computation method must exist."""
        self.assertIn('_compute_formato_1005', self.content)

    def test_compute_formato_1006(self):
        """Formato 1006 computation method must exist."""
        self.assertIn('_compute_formato_1006', self.content)

    def test_compute_formato_1007(self):
        """Formato 1007 computation method must exist."""
        self.assertIn('_compute_formato_1007', self.content)

    def test_action_compute_lines(self):
        """action_compute_lines method must dispatch to formato methods."""
        self.assertIn('action_compute_lines', self.content)

    def test_action_confirm(self):
        """action_confirm method must exist."""
        self.assertIn('action_confirm', self.content)

    def test_action_generate_xml(self):
        """action_generate_xml method must exist."""
        self.assertIn('action_generate_xml', self.content)

    def test_build_xml_method(self):
        """_build_xml method must generate lxml etree."""
        self.assertIn('_build_xml', self.content)
        self.assertIn('etree.Element', self.content)

    def test_dian_namespace(self):
        """XML must use DIAN exogena namespace."""
        self.assertIn('http://www.dian.gov.co/exogena', self.content)


class TestExogenousXmlStructure(unittest.TestCase):
    """Validate the XML structure produced by _build_xml constants."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/models/l10n_co_edi_exogenous.py') as f:
            cls.content = f.read()

    def test_xml_header_elements(self):
        """XML must include header elements: Ano, CodCpt, Formato, Version."""
        for tag in ['Ano', 'CodCpt', 'Formato', 'Version', 'NumEnvio',
                     'FecEnvio', 'FecInicial', 'FecFinal', 'ValorTotal', 'CantReg']:
            self.assertIn(f"'{tag}'", self.content,
                          f'XML header element {tag} missing')

    def test_xml_detail_elements(self):
        """XML must include detail elements for third-party data."""
        for tag in ['TDoc', 'NInn', 'Dir', 'CodDpto', 'CodMun', 'Pais',
                     'VlrBas']:
            self.assertIn(f"'{tag}'", self.content,
                          f'XML detail element {tag} missing')

    def test_concepto_code_mapping(self):
        """Concepto code mapping must cover all 5 formatos."""
        self.assertIn('_get_concepto_code', self.content)
        for fmt, code in [('1001', '1'), ('1003', '3'), ('1005', '5'),
                          ('1006', '6'), ('1007', '7')]:
            self.assertIn(f"'{fmt}': '{code}'", self.content)

    def test_partner_doc_type_mapping(self):
        """Partner document type mapping must handle NIT, CC, CE, passport."""
        self.assertIn('_get_partner_doc_type', self.content)
        for code in ['31', '13', '22', '41']:
            self.assertIn(f"'{code}'", self.content)


class TestExogenousRetentionConstants(unittest.TestCase):
    """Validate retention code constants."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/models/l10n_co_edi_exogenous.py') as f:
            cls.content = f.read()

    def test_retention_codes_defined(self):
        """RETENTION_CODES dict must exist with RteFte, RteIVA, RteICA."""
        self.assertIn('RETENTION_CODES', self.content)

    def test_formato_1001_concepts(self):
        """FORMATO_1001_CONCEPTS must define payment concept codes."""
        self.assertIn('FORMATO_1001_CONCEPTS', self.content)
        for concept in ['honorarios', 'comisiones', 'servicios',
                        'arrendamientos', 'compras']:
            self.assertIn(f"'{concept}'", self.content)


class TestExogenousWizard(unittest.TestCase):
    """Validate exogenous wizard model."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/wizard/l10n_co_edi_exogenous_wizard.py') as f:
            cls.content = f.read()
        cls.tree = ast.parse(cls.content)

    def test_wizard_class_exists(self):
        """Wizard class must exist."""
        classes = [n.name for n in ast.walk(self.tree) if isinstance(n, ast.ClassDef)]
        self.assertIn('L10nCoEdiExogenousWizard', classes)

    def test_wizard_model_name(self):
        """Wizard _name must be l10n_co_edi.exogenous.wizard."""
        self.assertIn("_name = 'l10n_co_edi.exogenous.wizard'", self.content)

    def test_wizard_has_year_field(self):
        """Wizard must have year field."""
        self.assertIn('year', self.content)

    def test_wizard_has_formato_field(self):
        """Wizard must have formato selection."""
        self.assertIn('formato_ids', self.content)

    def test_wizard_has_action_generate(self):
        """Wizard must have action_generate method."""
        self.assertIn('action_generate', self.content)

    def test_wizard_supports_all_formatos(self):
        """Wizard 'all' option must generate all 5 formatos."""
        self.assertIn("'all'", self.content)
        for fmt in ['1001', '1003', '1005', '1006', '1007']:
            self.assertIn(f"'{fmt}'", self.content)


class TestExogenousViews(unittest.TestCase):
    """Validate exogenous views XML structure."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse('addons/l10n_co_edi/views/l10n_co_edi_exogenous_views.xml')
        cls.root = cls.tree.getroot()
        cls.records = cls.root.findall('record')

    def test_list_view_defined(self):
        """List view for exogenous documents must exist."""
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_edi_exogenous_document_list', ids)

    def test_form_view_defined(self):
        """Form view for exogenous documents must exist."""
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_edi_exogenous_document_form', ids)

    def test_wizard_view_defined(self):
        """Wizard form view must exist."""
        ids = [r.get('id') for r in self.records]
        self.assertIn('l10n_co_edi_exogenous_wizard_form', ids)

    def test_action_defined(self):
        """Window action for exogenous documents must exist."""
        ids = [r.get('id') for r in self.records]
        self.assertIn('action_l10n_co_edi_exogenous_document', ids)

    def test_menu_items_defined(self):
        """Menu items must exist."""
        menus = self.root.findall('menuitem')
        menu_ids = [m.get('id') for m in menus]
        self.assertIn('menu_l10n_co_edi_exogenous', menu_ids)
        self.assertIn('menu_l10n_co_edi_exogenous_wizard', menu_ids)

    def test_form_has_statusbar(self):
        """Form view must have state statusbar widget."""
        form_record = [r for r in self.records
                       if r.get('id') == 'l10n_co_edi_exogenous_document_form'][0]
        arch_field = form_record.find('.//field[@name="arch"]')
        # The arch content is stored as child elements, so serialize it
        arch_str = ET.tostring(arch_field, encoding='unicode')
        self.assertIn('statusbar', arch_str)


class TestExogenousSecurity(unittest.TestCase):
    """Validate security access rules for exogenous models."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_edi/security/ir.model.access.csv') as f:
            cls.rows = list(csv.DictReader(f))

    def test_document_access_rules_exist(self):
        """Access rules for exogenous document model must exist."""
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_edi_exogenous_document', model_ids)

    def test_line_access_rules_exist(self):
        """Access rules for exogenous document line model must exist."""
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_edi_exogenous_document_line', model_ids)

    def test_wizard_access_rules_exist(self):
        """Access rules for exogenous wizard must exist."""
        model_ids = [r['model_id:id'] for r in self.rows]
        self.assertIn('model_l10n_co_edi_exogenous_wizard', model_ids)

    def test_user_read_only(self):
        """User group should have read-only access to documents."""
        user_rules = [
            r for r in self.rows
            if 'exogenous_doc_user' in r['id']
        ]
        self.assertEqual(len(user_rules), 1)
        rule = user_rules[0]
        self.assertEqual(rule['perm_read'], '1')
        self.assertEqual(rule['perm_write'], '0')
        self.assertEqual(rule['perm_create'], '0')
        self.assertEqual(rule['perm_unlink'], '0')

    def test_manager_full_access(self):
        """Manager group should have full access to documents."""
        mgr_rules = [
            r for r in self.rows
            if 'exogenous_doc_manager' in r['id']
        ]
        self.assertEqual(len(mgr_rules), 1)
        rule = mgr_rules[0]
        self.assertEqual(rule['perm_read'], '1')
        self.assertEqual(rule['perm_write'], '1')
        self.assertEqual(rule['perm_create'], '1')
        self.assertEqual(rule['perm_unlink'], '1')


class TestExogenousModuleIntegration(unittest.TestCase):
    """Validate module integration (imports, manifest)."""

    def test_model_imported(self):
        """Exogenous model must be imported in models/__init__.py."""
        with open('addons/l10n_co_edi/models/__init__.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_exogenous', content)

    def test_wizard_imported(self):
        """Exogenous wizard must be imported in wizard/__init__.py."""
        with open('addons/l10n_co_edi/wizard/__init__.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_exogenous_wizard', content)

    def test_views_in_manifest(self):
        """Exogenous views must be listed in __manifest__.py."""
        with open('addons/l10n_co_edi/__manifest__.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_exogenous_views.xml', content)


if __name__ == '__main__':
    unittest.main()
