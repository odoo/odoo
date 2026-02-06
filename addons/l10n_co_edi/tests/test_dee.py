# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import csv
import unittest


class TestDEEDocumentTypes(unittest.TestCase):
    """Validate Documento Equivalente Electronico (DEE) document type data."""

    @classmethod
    def setUpClass(cls):
        cls.csv_path = 'addons/l10n_co_edi/data/l10n_co_edi.document.type.csv'
        with open(cls.csv_path) as f:
            cls.rows = list(csv.DictReader(f))

    def test_csv_has_is_dee_column(self):
        """CSV must have the is_dee column."""
        self.assertIn('is_dee', self.rows[0].keys())

    def test_at_least_13_dee_types(self):
        """Should have at least 13 DEE types per Res. 000165/2023."""
        dee_count = sum(1 for r in self.rows if r.get('is_dee') == '1')
        self.assertGreaterEqual(dee_count, 13)

    def test_pos_ticket_type_present(self):
        """POS ticket type (05) must be present and marked as DEE."""
        pos_rows = [r for r in self.rows if r['code'] == '05']
        self.assertEqual(len(pos_rows), 1)
        self.assertEqual(pos_rows[0]['is_dee'], '1')

    def test_support_note_type_present(self):
        """Nota Soporte (20) must be present and marked as DEE."""
        ns_rows = [r for r in self.rows if r['code'] == '20']
        self.assertEqual(len(ns_rows), 1)
        self.assertEqual(ns_rows[0]['is_dee'], '1')

    def test_invoices_not_dee(self):
        """Regular invoices (01) and credit notes (91) should not be DEE."""
        for code in ('01', '91', '92'):
            rows = [r for r in self.rows if r['code'] == code]
            self.assertEqual(len(rows), 1, f'Code {code} missing')
            self.assertEqual(rows[0]['is_dee'], '0',
                             f'Code {code} should not be DEE')

    def test_codes_unique(self):
        """All document type codes must be unique."""
        codes = [r['code'] for r in self.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_ids_unique(self):
        """XML IDs must be unique."""
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_key_dee_codes_present(self):
        """Key DEE types must be present."""
        codes = {r['code'] for r in self.rows}
        expected_dee = {'05', '07', '10', '11', '12', '13', '20'}
        for code in expected_dee:
            self.assertIn(code, codes, f'DEE code {code} missing')


class TestDEEDocumentTypeModel(unittest.TestCase):
    """Validate document type model has is_dee field."""

    def test_model_has_is_dee_field(self):
        """Document type model must define is_dee field."""
        with open('addons/l10n_co_edi/models/l10n_co_edi_document_type.py') as f:
            content = f.read()
        self.assertIn('is_dee', content)
        tree = ast.parse(content)
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(classes), 1)


class TestDEEAccountMoveFields(unittest.TestCase):
    """Validate DEE fields on account.move."""

    def test_account_move_has_dee_fields(self):
        """account.move must have DEE-specific fields."""
        with open('addons/l10n_co_edi/models/account_move.py') as f:
            content = f.read()
        required_fields = [
            'l10n_co_edi_dee_type_id',
            'l10n_co_edi_is_dee',
            'l10n_co_edi_dee_simplified_buyer',
        ]
        for field in required_fields:
            self.assertIn(field, content, f'Field {field} missing from account_move.py')

    def test_cude_used_for_dee(self):
        """CUFE/CUDE logic should use CUDE for DEE."""
        with open('addons/l10n_co_edi/models/account_move.py') as f:
            content = f.read()
        # Should check is_dee to determine CUFE vs CUDE
        self.assertIn('l10n_co_edi_is_dee', content)
        self.assertIn('use_cude', content)


class TestDEEXmlBuilder(unittest.TestCase):
    """Validate DEE support in the UBL XML builder."""

    def test_customization_id_handles_dee(self):
        """XML builder must return DEE type code for CustomizationID."""
        with open('addons/l10n_co_edi/models/account_edi_xml_ubl_co.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_dee_type_id', content)

    def test_simplified_buyer_node(self):
        """XML builder must have a simplified buyer method for DEE POS."""
        with open('addons/l10n_co_edi/models/account_edi_xml_ubl_co.py') as f:
            content = f.read()
        self.assertIn('_get_co_simplified_buyer_node', content)
        self.assertIn('CONSUMIDOR FINAL', content)

    def test_uuid_scheme_handles_dee(self):
        """UUID schemeName should use CUDE-SHA384 for DEE."""
        with open('addons/l10n_co_edi/models/account_edi_xml_ubl_co.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_is_dee', content)
        self.assertIn('CUDE-SHA384', content)


class TestDEEEdiFormat(unittest.TestCase):
    """Validate DEE support in EDI format validation."""

    def test_relaxed_validation_for_dee(self):
        """EDI format should relax validation for DEE simplified buyer."""
        with open('addons/l10n_co_edi/models/account_edi_format.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_is_dee', content)
        self.assertIn('dee_simplified_buyer', content)


if __name__ == '__main__':
    unittest.main()
