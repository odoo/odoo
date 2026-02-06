# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import csv
import unittest
from lxml import etree


class TestFiscalResponsibilityData(unittest.TestCase):
    """Validate DIAN fiscal responsibility reference data."""

    @classmethod
    def setUpClass(cls):
        cls.csv_path = 'addons/l10n_co_edi/data/l10n_co_edi.fiscal.responsibility.csv'
        with open(cls.csv_path) as f:
            cls.rows = list(csv.DictReader(f))

    def test_csv_has_required_columns(self):
        """CSV must have id, code, and name columns."""
        self.assertIn('id', self.rows[0].keys())
        self.assertIn('code', self.rows[0].keys())
        self.assertIn('name', self.rows[0].keys())

    def test_at_least_10_responsibilities(self):
        """Should have at least 10 DIAN fiscal responsibility codes."""
        self.assertGreaterEqual(len(self.rows), 10)

    def test_codes_unique(self):
        """All codes must be unique."""
        codes = [r['code'] for r in self.rows]
        self.assertEqual(len(codes), len(set(codes)),
                         f'Duplicate codes: {[c for c in codes if codes.count(c) > 1]}')

    def test_key_codes_present(self):
        """Key DIAN codes must be present."""
        codes = {r['code'] for r in self.rows}
        required = {'O-13', 'O-15', 'O-47', 'O-48', 'O-49', 'R-99-PN'}
        for code in required:
            self.assertIn(code, codes, f'Required code {code} missing')

    def test_ids_unique(self):
        """XML IDs must be unique."""
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))


class TestFiscalPositionData(unittest.TestCase):
    """Validate Colombian fiscal position XML data."""

    @classmethod
    def setUpClass(cls):
        cls.xml_path = 'addons/l10n_co_edi/data/account_fiscal_position_data.xml'
        cls.tree = etree.parse(cls.xml_path)
        cls.root = cls.tree.getroot()

    def test_xml_valid(self):
        """Fiscal position XML must be well-formed."""
        self.assertIsNotNone(self.root)
        self.assertEqual(self.root.tag, 'odoo')

    def test_fiscal_positions_defined(self):
        """Should define at least 4 fiscal positions."""
        fps = self.root.findall(".//record[@model='account.fiscal.position']")
        self.assertGreaterEqual(len(fps), 4)

    def test_key_positions_present(self):
        """Key fiscal positions must be present."""
        fp_ids = {
            r.get('id') for r in
            self.root.findall(".//record[@model='account.fiscal.position']")
        }
        expected = {
            'fiscal_position_co_gran_contribuyente',
            'fiscal_position_co_regimen_simple',
            'fiscal_position_co_no_responsable',
            'fiscal_position_co_domestic',
            'fiscal_position_co_foreign',
        }
        for fp_id in expected:
            self.assertIn(fp_id, fp_ids, f'Fiscal position {fp_id} missing')

    def test_auto_apply_set(self):
        """All fiscal positions should have auto_apply enabled."""
        for fp in self.root.findall(".//record[@model='account.fiscal.position']"):
            auto_apply = fp.find("field[@name='auto_apply']")
            self.assertIsNotNone(auto_apply,
                                 f'FP {fp.get("id")} missing auto_apply')

    def test_sequences_defined(self):
        """All fiscal positions should have a sequence for priority ordering."""
        for fp in self.root.findall(".//record[@model='account.fiscal.position']"):
            sequence = fp.find("field[@name='sequence']")
            self.assertIsNotNone(sequence,
                                 f'FP {fp.get("id")} missing sequence')

    def test_gran_contribuyente_has_higher_priority(self):
        """Gran Contribuyente should have higher priority (lower sequence) than domestic."""
        fps = {}
        for fp in self.root.findall(".//record[@model='account.fiscal.position']"):
            seq = fp.find("field[@name='sequence']")
            if seq is not None:
                fps[fp.get('id')] = int(seq.text)

        self.assertLess(
            fps.get('fiscal_position_co_gran_contribuyente', 999),
            fps.get('fiscal_position_co_domestic', 0),
            'Gran Contribuyente should have lower sequence than domestic'
        )


class TestPartnerModel(unittest.TestCase):
    """Validate partner extension for Colombian tax classification."""

    def test_partner_model_parseable(self):
        """Partner extension must be valid Python."""
        with open('addons/l10n_co_edi/models/res_partner.py') as f:
            tree = ast.parse(f.read())
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, 'ResPartner')

    def test_partner_has_required_fields(self):
        """Partner model must define key classification fields."""
        with open('addons/l10n_co_edi/models/res_partner.py') as f:
            content = f.read()
        required_fields = [
            'l10n_co_edi_tax_regime',
            'l10n_co_edi_gran_contribuyente',
            'l10n_co_edi_autorretenedor',
            'l10n_co_edi_fiscal_responsibility_ids',
            'l10n_co_edi_ciiu_code',
        ]
        for field in required_fields:
            self.assertIn(field, content, f'Field {field} not found in res_partner.py')


class TestFiscalPositionModel(unittest.TestCase):
    """Validate fiscal position extension."""

    def test_fp_model_parseable(self):
        """Fiscal position extension must be valid Python."""
        with open('addons/l10n_co_edi/models/account_fiscal_position.py') as f:
            tree = ast.parse(f.read())
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, 'AccountFiscalPosition')

    def test_fp_has_filter_fields(self):
        """FP model must define Colombian filter fields."""
        with open('addons/l10n_co_edi/models/account_fiscal_position.py') as f:
            content = f.read()
        self.assertIn('l10n_co_edi_tax_regime', content)
        self.assertIn('l10n_co_edi_gran_contribuyente', content)
        self.assertIn('_get_fpos_validation_functions', content)


class TestFiscalResponsibilityModel(unittest.TestCase):
    """Validate fiscal responsibility model."""

    def test_model_parseable(self):
        """Fiscal responsibility model must be valid Python."""
        with open('addons/l10n_co_edi/models/l10n_co_edi_fiscal_responsibility.py') as f:
            tree = ast.parse(f.read())
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, 'L10nCoEdiFiscalResponsibility')


class TestXmlBuilderUpdate(unittest.TestCase):
    """Validate that XML builder uses partner fiscal data for customers."""

    def test_xml_builder_uses_partner_fiscal_resp(self):
        """XML builder should read customer fiscal responsibilities from partner."""
        with open('addons/l10n_co_edi/models/account_edi_xml_ubl_co.py') as f:
            content = f.read()
        # Should reference partner's fiscal responsibilities for customer role
        self.assertIn('l10n_co_edi_fiscal_responsibilities', content)
        # Should check commercial partner for customer regime
        self.assertIn('commercial.l10n_co_edi_tax_regime', content)


if __name__ == '__main__':
    unittest.main()
