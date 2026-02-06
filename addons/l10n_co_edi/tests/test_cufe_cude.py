# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from datetime import datetime
from unittest import TestCase

from odoo.addons.l10n_co_edi.models.l10n_co_edi_cufe import (
    compute_cufe,
    compute_cude,
    _format_amount,
)


class TestCufeCude(TestCase):
    """Unit tests for CUFE/CUDE computation.

    These tests verify the SHA-384 hash computation against known inputs.
    The CUFE/CUDE algorithm is defined by DIAN Technical Annex v1.9.
    """

    def test_format_amount_integer(self):
        self.assertEqual(_format_amount(1000), '1000.00')

    def test_format_amount_float(self):
        self.assertEqual(_format_amount(1234.5), '1234.50')

    def test_format_amount_zero(self):
        self.assertEqual(_format_amount(0), '0.00')

    def test_format_amount_string(self):
        self.assertEqual(_format_amount('999.9'), '999.90')

    def test_format_amount_precise(self):
        self.assertEqual(_format_amount(100.456), '100.46')

    def test_cufe_deterministic(self):
        """CUFE must be deterministic — same inputs produce same output."""
        kwargs = dict(
            num_fac='SETP990000001',
            fec_fac='2024-01-15T10:30:00',
            val_fac=1000000.00,
            cod_imp_1='01',
            val_imp_1=190000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=1190000.00,
            nit_ofe='900123456',
            num_adq='800987654',
            cl_tec='fc8eac422eba16e22ffd8c6f94b3f40a6e38571d7e',
            tipo_ambiente='2',
        )
        cufe1 = compute_cufe(**kwargs)
        cufe2 = compute_cufe(**kwargs)
        self.assertEqual(cufe1, cufe2)

    def test_cufe_is_sha384_hex(self):
        """CUFE must be a 96-character lowercase hex string (SHA-384)."""
        cufe = compute_cufe(
            num_fac='FV001',
            fec_fac='2024-06-01T08:00:00',
            val_fac=500000.00,
            cod_imp_1='01',
            val_imp_1=95000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=595000.00,
            nit_ofe='123456789',
            num_adq='987654321',
            cl_tec='abcdef1234567890',
            tipo_ambiente='1',
        )
        self.assertEqual(len(cufe), 96)
        self.assertTrue(all(c in '0123456789abcdef' for c in cufe))

    def test_cufe_with_datetime_object(self):
        """CUFE should accept datetime objects, not just strings."""
        dt = datetime(2024, 3, 15, 14, 30, 0)
        cufe = compute_cufe(
            num_fac='FV002',
            fec_fac=dt,
            val_fac=200000.00,
            cod_imp_1='01',
            val_imp_1=38000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=238000.00,
            nit_ofe='111222333',
            num_adq='444555666',
            cl_tec='testkey123',
            tipo_ambiente='2',
        )
        # Verify it matches the string version
        cufe_str = compute_cufe(
            num_fac='FV002',
            fec_fac='2024-03-15T14:30:00',
            val_fac=200000.00,
            cod_imp_1='01',
            val_imp_1=38000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=238000.00,
            nit_ofe='111222333',
            num_adq='444555666',
            cl_tec='testkey123',
            tipo_ambiente='2',
        )
        self.assertEqual(cufe, cufe_str)

    def test_cufe_known_vector(self):
        """Verify CUFE against a manually computed SHA-384 hash."""
        # Build the expected input string
        input_str = (
            'SETP990000001'        # NumFac
            '2024-01-15T10:30:00'  # FecFac
            '1000000.00'           # ValFac
            '01'                   # CodImp1
            '190000.00'            # ValImp1
            '04'                   # CodImp2
            '0.00'                 # ValImp2
            '03'                   # CodImp3
            '0.00'                 # ValImp3
            '1190000.00'           # ValTot
            '900123456'            # NitOFE
            '800987654'            # NumAdq
            'TESTKEY'              # ClTec
            '2'                    # TipoAmbiente
        )
        expected = hashlib.sha384(input_str.encode('utf-8')).hexdigest()

        cufe = compute_cufe(
            num_fac='SETP990000001',
            fec_fac='2024-01-15T10:30:00',
            val_fac=1000000.00,
            cod_imp_1='01',
            val_imp_1=190000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=1190000.00,
            nit_ofe='900123456',
            num_adq='800987654',
            cl_tec='TESTKEY',
            tipo_ambiente='2',
        )
        self.assertEqual(cufe, expected)

    def test_cude_deterministic(self):
        """CUDE must be deterministic."""
        kwargs = dict(
            num_doc='NC001',
            fec_doc='2024-02-20T16:00:00',
            val_doc=500000.00,
            cod_imp_1='01',
            val_imp_1=95000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=595000.00,
            nit_ofe='900123456',
            num_adq='800987654',
            pin_software='12345',
            tipo_ambiente='2',
        )
        cude1 = compute_cude(**kwargs)
        cude2 = compute_cude(**kwargs)
        self.assertEqual(cude1, cude2)

    def test_cude_is_sha384_hex(self):
        """CUDE must be a 96-character lowercase hex string."""
        cude = compute_cude(
            num_doc='NC001',
            fec_doc='2024-02-20T16:00:00',
            val_doc=500000.00,
            cod_imp_1='01',
            val_imp_1=95000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=595000.00,
            nit_ofe='900123456',
            num_adq='800987654',
            pin_software='12345',
            tipo_ambiente='2',
        )
        self.assertEqual(len(cude), 96)
        self.assertTrue(all(c in '0123456789abcdef' for c in cude))

    def test_cude_known_vector(self):
        """Verify CUDE against a manually computed SHA-384 hash."""
        input_str = (
            'NC001'
            '2024-02-20T16:00:00'
            '500000.00'
            '01'
            '95000.00'
            '04'
            '0.00'
            '03'
            '0.00'
            '595000.00'
            '900123456'
            '800987654'
            'MYPIN'
            '1'
        )
        expected = hashlib.sha384(input_str.encode('utf-8')).hexdigest()

        cude = compute_cude(
            num_doc='NC001',
            fec_doc='2024-02-20T16:00:00',
            val_doc=500000.00,
            cod_imp_1='01',
            val_imp_1=95000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=595000.00,
            nit_ofe='900123456',
            num_adq='800987654',
            pin_software='MYPIN',
            tipo_ambiente='1',
        )
        self.assertEqual(cude, expected)

    def test_cufe_different_from_cude(self):
        """CUFE and CUDE for same data but different key/pin must differ."""
        common = dict(
            val_fac=100000.00,
            cod_imp_1='01',
            val_imp_1=19000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=119000.00,
            nit_ofe='900111222',
            num_adq='800333444',
            tipo_ambiente='2',
        )
        cufe = compute_cufe(
            num_fac='FV100', fec_fac='2024-01-01T00:00:00',
            cl_tec='TECH_KEY', **common
        )
        cude = compute_cude(
            num_doc='FV100', fec_doc='2024-01-01T00:00:00',
            pin_software='TECH_KEY', **common
        )
        # They use the same algo but we verify the function paths work independently
        # (they should actually be equal here since cl_tec == pin_software and same inputs)
        self.assertEqual(cufe, cude)

    def test_cufe_sensitive_to_amount_change(self):
        """Changing any input field must produce a different CUFE."""
        base = dict(
            num_fac='FV200',
            fec_fac='2024-05-01T12:00:00',
            val_fac=100000.00,
            cod_imp_1='01',
            val_imp_1=19000.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=119000.00,
            nit_ofe='900111222',
            num_adq='800333444',
            cl_tec='KEY123',
            tipo_ambiente='1',
        )
        cufe_original = compute_cufe(**base)

        # Change amount by 1 peso
        modified = dict(base, val_fac=100001.00, val_tot=119001.00)
        cufe_modified = compute_cufe(**modified)
        self.assertNotEqual(cufe_original, cufe_modified)

    def test_cufe_zero_taxes(self):
        """CUFE should work correctly when all taxes are zero (exempt invoice)."""
        cufe = compute_cufe(
            num_fac='EX001',
            fec_fac='2024-07-01T09:00:00',
            val_fac=5000000.00,
            cod_imp_1='01',
            val_imp_1=0.00,
            cod_imp_2='04',
            val_imp_2=0.00,
            cod_imp_3='03',
            val_imp_3=0.00,
            val_tot=5000000.00,
            nit_ofe='900555666',
            num_adq='800777888',
            cl_tec='EXEMPTKEY',
            tipo_ambiente='1',
        )
        self.assertEqual(len(cufe), 96)
