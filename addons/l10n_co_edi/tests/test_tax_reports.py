# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import unittest
from lxml import etree


class TestTaxReportData(unittest.TestCase):
    """Validate Colombian tax report XML data structure."""

    @classmethod
    def setUpClass(cls):
        cls.report_xml_path = (
            'addons/l10n_co/data/account_tax_report_data.xml'
        )
        cls.tree = etree.parse(cls.report_xml_path)
        cls.root = cls.tree.getroot()

    def test_xml_valid(self):
        """Report XML must be well-formed."""
        self.assertIsNotNone(self.root)
        self.assertEqual(self.root.tag, 'odoo')

    def test_two_reports_defined(self):
        """There should be two account.report records (F300 + F350)."""
        reports = self.root.findall(".//record[@model='account.report']")
        self.assertEqual(len(reports), 2)
        report_ids = {r.get('id') for r in reports}
        self.assertIn('tax_report_co_iva', report_ids)
        self.assertIn('tax_report_co_withholding', report_ids)

    def test_f300_has_report_lines(self):
        """Formulario 300 must have report lines."""
        lines = self.root.findall(
            ".//record[@model='account.report.line']"
        )
        # Should have at least 10 lines (sections + detail)
        self.assertGreater(len(lines), 10)

    def test_f300_line_codes_unique(self):
        """All report line codes must be unique within the file."""
        codes = []
        for record in self.root.findall(
            ".//record[@model='account.report.line']"
        ):
            for field in record.findall("field[@name='code']"):
                if field.text:
                    codes.append(field.text)

        self.assertEqual(len(codes), len(set(codes)),
                         f'Duplicate codes found: {[c for c in codes if codes.count(c) > 1]}')

    def test_tax_tag_formulas_reference_known_tags(self):
        """All tax_tags expressions must reference tags that exist in the CSV."""
        # Collect tag names from CSV
        csv_tags = set()
        csv_path = 'addons/l10n_co/data/template/account.tax-co.csv'
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                tag = (row.get('repartition_line_ids/tag_ids') or '').strip()
                if tag:
                    csv_tags.add(tag)

        # Collect formula references from report expressions
        for expr in self.root.findall(
            ".//record[@model='account.report.expression']"
        ):
            engine_field = expr.find("field[@name='engine']")
            formula_field = expr.find("field[@name='formula']")
            if engine_field is not None and engine_field.text == 'tax_tags':
                formula = formula_field.text.lstrip('-')
                self.assertIn(
                    formula, csv_tags,
                    f'Formula "{formula}" in expression {expr.get("id")} '
                    f'not found in tax CSV tag_ids'
                )

    def test_expressions_have_valid_engines(self):
        """All expressions must use valid engine types."""
        valid_engines = {'tax_tags', 'aggregation', 'domain', 'external',
                         'account_codes', 'custom'}
        for expr in self.root.findall(
            ".//record[@model='account.report.expression']"
        ):
            engine_field = expr.find("field[@name='engine']")
            if engine_field is not None and engine_field.text:
                self.assertIn(engine_field.text, valid_engines)

    def test_country_id_set(self):
        """Both reports must have country_id set to Colombia."""
        for report in self.root.findall(".//record[@model='account.report']"):
            country_field = report.find("field[@name='country_id']")
            self.assertIsNotNone(country_field)
            self.assertEqual(country_field.get('ref'), 'base.co')


class TestTaxCSVIntegrity(unittest.TestCase):
    """Validate the Colombian tax CSV structure and tag assignments."""

    @classmethod
    def setUpClass(cls):
        cls.csv_path = 'addons/l10n_co/data/template/account.tax-co.csv'
        with open(cls.csv_path) as f:
            cls.rows = list(csv.DictReader(f))

    def test_csv_has_tag_column(self):
        """CSV must have the repartition_line_ids/tag_ids column."""
        self.assertIn('repartition_line_ids/tag_ids', self.rows[0].keys())

    def test_all_iva_taxes_have_tags(self):
        """IVA purchase/sale taxes (non-group) with amount > 0 should have tags."""
        current_tax_id = None
        for row in self.rows:
            if row['id']:
                current_tax_id = row['id']
            # Skip group taxes and counterparts
            if row.get('amount_type') == 'group':
                continue
            if not current_tax_id:
                continue

            # Check IVA taxes (non-zero, non-counterpart)
            name = (row.get('name') or '').upper()
            if 'IVA' in name or 'VAT' in (row.get('description') or '').upper():
                tag = (row.get('repartition_line_ids/tag_ids') or '').strip()
                rep_type = (row.get('repartition_line_ids/repartition_type') or '').strip()
                # base lines of IVA taxes should have tags (unless 0% counterpart)
                if rep_type == 'base' and tag:
                    self.assertTrue(
                        tag.startswith('IVA_') or tag.startswith('RTEIVA_'),
                        f'Tax {current_tax_id}: expected IVA/RTEIVA tag prefix, got {tag}'
                    )

    def test_rtefte_taxes_have_tags(self):
        """RteFte taxes should have withholding tags."""
        current_tax_id = None
        for row in self.rows:
            if row['id']:
                current_tax_id = row['id']
            if not current_tax_id or row.get('amount_type') == 'group':
                continue

            name = (row.get('name') or '').upper()
            if 'RTEFTE' in name or 'RTEFTE' in (row.get('description') or '').upper():
                tag = (row.get('repartition_line_ids/tag_ids') or '').strip()
                rep_type = (row.get('repartition_line_ids/repartition_type') or '').strip()
                if rep_type == 'base' and tag:
                    self.assertTrue(
                        tag.startswith('RTEFTE_'),
                        f'Tax {current_tax_id}: expected RTEFTE_ prefix, got {tag}'
                    )

    def test_tag_names_follow_convention(self):
        """All tag names should follow the naming convention."""
        valid_prefixes = (
            'IVA_', 'INC_', 'RTEFTE_', 'RTEIVA_', 'RTEICA_',
        )
        for row in self.rows:
            tag = (row.get('repartition_line_ids/tag_ids') or '').strip()
            if tag:
                self.assertTrue(
                    any(tag.startswith(p) for p in valid_prefixes),
                    f'Tag "{tag}" does not start with a valid prefix'
                )


class TestWithholdingCertModel(unittest.TestCase):
    """Validate withholding certificate model structure."""

    def test_model_file_parseable(self):
        """Withholding certificate Python file must be valid."""
        import ast
        with open('addons/l10n_co_edi/models/l10n_co_withholding_cert.py') as f:
            tree = ast.parse(f.read())
        # Should define two classes
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        class_names = {c.name for c in classes}
        self.assertIn('L10nCoWithholdingCertificate', class_names)
        self.assertIn('L10nCoWithholdingCertificateLine', class_names)

    def test_wizard_file_parseable(self):
        """Wizard Python file must be valid."""
        import ast
        with open('addons/l10n_co_edi/wizard/l10n_co_withholding_cert_wizard.py') as f:
            tree = ast.parse(f.read())
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, 'L10nCoWithholdingCertificateWizard')


if __name__ == '__main__':
    unittest.main()
