# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestUvt(TransactionCase):
    """Tests for UVT management model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UVT = cls.env['l10n_co_edi.uvt']
        cls.company = cls.env.company

        # Create test UVT records
        cls.uvt_2025 = cls.UVT.create({
            'year': 2025,
            'value': 49799,
            'resolution': 'Test Res 2025',
            'company_id': cls.company.id,
        })
        cls.uvt_2026 = cls.UVT.create({
            'year': 2026,
            'value': 52374,
            'resolution': 'Test Res 2026',
            'company_id': cls.company.id,
        })

    def test_get_uvt_value(self):
        """Get UVT value for a specific year."""
        value = self.UVT.get_uvt_value(year=2026, company=self.company)
        self.assertEqual(value, 52374)

    def test_get_uvt_value_missing_year(self):
        """Missing year should return 0."""
        value = self.UVT.get_uvt_value(year=1999, company=self.company)
        self.assertEqual(value, 0.0)

    def test_convert_uvt_to_cop(self):
        """Convert UVTs to COP."""
        # 10 UVT at 2026 rate = 523,740 COP
        cop = self.UVT.convert_uvt_to_cop(10, year=2026, company=self.company)
        self.assertEqual(cop, 523740)

    def test_convert_cop_to_uvt(self):
        """Convert COP to UVTs."""
        uvt = self.UVT.convert_cop_to_uvt(523740, year=2026, company=self.company)
        self.assertAlmostEqual(uvt, 10.0, places=2)

    def test_convert_cop_to_uvt_missing_value(self):
        """Missing UVT value should return 0."""
        uvt = self.UVT.convert_cop_to_uvt(100000, year=1999, company=self.company)
        self.assertEqual(uvt, 0.0)

    def test_unique_year_company(self):
        """Cannot create duplicate UVT for same year and company."""
        with self.assertRaises(Exception):
            self.UVT.create({
                'year': 2026,
                'value': 99999,
                'company_id': self.company.id,
            })

    def test_value_must_be_positive(self):
        """UVT value must be greater than zero."""
        with self.assertRaises(Exception):
            self.UVT.create({
                'year': 2030,
                'value': 0,
                'company_id': self.company.id,
            })

    def test_uvt_ordering(self):
        """UVT records should be ordered by year descending."""
        records = self.UVT.search([('company_id', '=', self.company.id)])
        years = records.mapped('year')
        self.assertEqual(years, sorted(years, reverse=True))

    def test_withholding_threshold_example(self):
        """Verify typical withholding threshold computation.

        Example: RteFte on purchases applies when base >= 27 UVT (2026).
        27 UVT * 52,374 = 1,414,098 COP
        """
        threshold_uvt = 27
        threshold_cop = self.UVT.convert_uvt_to_cop(threshold_uvt, year=2026, company=self.company)
        self.assertEqual(threshold_cop, 27 * 52374)

        # An invoice of 1,500,000 COP exceeds the threshold
        self.assertGreater(1500000, threshold_cop)
        # An invoice of 1,000,000 COP does not
        self.assertLess(1000000, threshold_cop)
