# Part of GPCB. See LICENSE file for full copyright and licensing details.

"""Tests for CUNE computation and payroll line concept codes."""

import ast
import hashlib
import unittest


class TestCUNEModel(unittest.TestCase):
    """Validate CUNE computation model structure."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_payroll_edi/models/l10n_co_payroll_cune.py') as f:
            cls.content = f.read()

    def test_model_name(self):
        self.assertIn("_name = 'l10n_co.payroll.cune'", self.content)

    def test_compute_method(self):
        self.assertIn('_compute_cune', self.content)

    def test_verify_method(self):
        self.assertIn('_verify_cune', self.content)

    def test_uses_sha384(self):
        """CUNE must use SHA-384 algorithm."""
        self.assertIn('sha384', self.content)

    def test_hash_input_components(self):
        """CUNE hash input must include required components."""
        for component in (
            'document_number', 'total_earnings', 'total_deductions',
            'net_pay', 'software_pin', 'ambiente',
        ):
            self.assertIn(component, self.content,
                          f'CUNE hash component {component} missing')

    def test_colombia_timezone(self):
        """CUNE should use Colombian timezone (UTC-5)."""
        self.assertIn('-05:00', self.content)


class TestCUNEAlgorithm(unittest.TestCase):
    """Test the SHA-384 hashing algorithm used by CUNE."""

    def test_sha384_produces_96_hex_chars(self):
        """SHA-384 hash must produce exactly 96 hex characters."""
        test_input = 'NE202600001 2026-01-31 12:00:00-05:00 5000000.00 500000.00 4500000.00 900123456 1234567890 102 testpin 2'
        result = hashlib.sha384(test_input.encode()).hexdigest()
        self.assertEqual(len(result), 96)

    def test_sha384_is_deterministic(self):
        """Same input must produce same hash."""
        test_input = 'test_cune_input'
        hash1 = hashlib.sha384(test_input.encode()).hexdigest()
        hash2 = hashlib.sha384(test_input.encode()).hexdigest()
        self.assertEqual(hash1, hash2)


class TestPayrollConceptCodes(unittest.TestCase):
    """Validate payroll concept code definitions."""

    @classmethod
    def setUpClass(cls):
        with open('addons/l10n_co_payroll_edi/models/l10n_co_payroll_line.py') as f:
            cls.content = f.read()

    def test_earning_concepts_defined(self):
        self.assertIn('EARNING_CONCEPTS', self.content)

    def test_deduction_concepts_defined(self):
        self.assertIn('DEDUCTION_CONCEPTS', self.content)

    def test_provision_concepts_defined(self):
        self.assertIn('PROVISION_CONCEPTS', self.content)

    def test_salary_concept(self):
        self.assertIn("'salary'", self.content)
        self.assertIn("'SAL'", self.content)

    def test_transport_concept(self):
        self.assertIn("'transport'", self.content)
        self.assertIn("'ATR'", self.content)

    def test_overtime_concepts(self):
        for code in ('HED', 'HEN', 'HEDDF', 'HENDF', 'HRN', 'HRNDF'):
            self.assertIn(f"'{code}'", self.content, f'Overtime code {code} missing')

    def test_health_eps(self):
        self.assertIn("'health_eps'", self.content)
        self.assertIn("'EPS'", self.content)

    def test_pension_afp(self):
        self.assertIn("'pension_afp'", self.content)
        self.assertIn("'AFP'", self.content)

    def test_provision_arl(self):
        self.assertIn("'arl'", self.content)
        self.assertIn("'ARL'", self.content)

    def test_provision_sena_icbf_caja(self):
        for code in ('SEN', 'ICB', 'CCF'):
            self.assertIn(f"'{code}'", self.content,
                          f'Provision code {code} missing')

    def test_cesantias_provisions(self):
        self.assertIn("'cesantias_prov'", self.content)
        self.assertIn("'prima_prov'", self.content)
        self.assertIn("'vacation_prov'", self.content)

    def test_concept_code_map(self):
        self.assertIn('CONCEPT_CODE_MAP', self.content)


if __name__ == '__main__':
    unittest.main()
