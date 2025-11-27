"""
Unit tests for DROM-COM territory management logic.

This test file validates the implementation of DROM-COM rules for French
e-invoicing/e-reporting reform.
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.l10n_fr_pdp_reports.utils import drom_com_territories


@tagged('post_install', 'post_install_l10n', '-at_install', 'drom_com')
class TestDromComTerritories(TransactionCase):
    """Test DROM-COM territory classification and mapping logic."""

    # -------------------------------------------------------------------------
    # Test Territory Detection
    # -------------------------------------------------------------------------

    def test_is_france_territory(self):
        """Test detection of French territories (metro + DROM-COM)."""
        # Metropolitan France
        self.assertTrue(drom_com_territories.is_france_territory('FR'))

        # DROM
        self.assertTrue(drom_com_territories.is_france_territory('GP'))
        self.assertTrue(drom_com_territories.is_france_territory('MQ'))
        self.assertTrue(drom_com_territories.is_france_territory('RE'))
        self.assertTrue(drom_com_territories.is_france_territory('GF'))
        self.assertTrue(drom_com_territories.is_france_territory('YT'))

        # COM
        self.assertTrue(drom_com_territories.is_france_territory('BL'))
        self.assertTrue(drom_com_territories.is_france_territory('MF'))
        self.assertTrue(drom_com_territories.is_france_territory('PM'))
        self.assertTrue(drom_com_territories.is_france_territory('PF'))
        self.assertTrue(drom_com_territories.is_france_territory('WF'))
        self.assertTrue(drom_com_territories.is_france_territory('TF'))
        self.assertTrue(drom_com_territories.is_france_territory('NC'))

        # Foreign countries
        self.assertFalse(drom_com_territories.is_france_territory('DE'))
        self.assertFalse(drom_com_territories.is_france_territory('BE'))
        self.assertFalse(drom_com_territories.is_france_territory('US'))

        # Edge cases
        self.assertFalse(drom_com_territories.is_france_territory(''))
        self.assertFalse(drom_com_territories.is_france_territory(None))

    def test_is_drom_com(self):
        """Test detection of DROM-COM territories (excluding metro)."""
        # Metropolitan France - NOT DROM-COM
        self.assertFalse(drom_com_territories.is_drom_com('FR'))

        # DROM - are DROM-COM
        self.assertTrue(drom_com_territories.is_drom_com('GP'))
        self.assertTrue(drom_com_territories.is_drom_com('MQ'))
        self.assertTrue(drom_com_territories.is_drom_com('RE'))
        self.assertTrue(drom_com_territories.is_drom_com('GF'))
        self.assertTrue(drom_com_territories.is_drom_com('YT'))

        # COM - are DROM-COM
        self.assertTrue(drom_com_territories.is_drom_com('NC'))
        self.assertTrue(drom_com_territories.is_drom_com('PF'))

        # Foreign countries
        self.assertFalse(drom_com_territories.is_drom_com('DE'))

    def test_get_territory_type(self):
        """Test territory type classification."""
        # Metropolitan France
        self.assertEqual(drom_com_territories.get_territory_type('FR'), 'metro')

        # DROM e-invoicing (Guadeloupe, Martinique, Réunion)
        self.assertEqual(drom_com_territories.get_territory_type('GP'), 'drom_einvoicing')
        self.assertEqual(drom_com_territories.get_territory_type('MQ'), 'drom_einvoicing')
        self.assertEqual(drom_com_territories.get_territory_type('RE'), 'drom_einvoicing')

        # DROM e-reporting (Guyane, Mayotte)
        self.assertEqual(drom_com_territories.get_territory_type('GF'), 'drom_ereporting')
        self.assertEqual(drom_com_territories.get_territory_type('YT'), 'drom_ereporting')

        # COM territories
        self.assertEqual(drom_com_territories.get_territory_type('BL'), 'com')
        self.assertEqual(drom_com_territories.get_territory_type('NC'), 'com')
        self.assertEqual(drom_com_territories.get_territory_type('PF'), 'com')

        # Foreign or invalid
        self.assertIsNone(drom_com_territories.get_territory_type('DE'))
        self.assertIsNone(drom_com_territories.get_territory_type(''))
        self.assertIsNone(drom_com_territories.get_territory_type(None))

    # -------------------------------------------------------------------------
    # Test E-invoicing vs E-reporting Rules
    # -------------------------------------------------------------------------

    def test_should_use_einvoicing_metro_to_metro(self):
        """Test: Metro France ↔ Metro France = E-invoicing."""
        self.assertTrue(drom_com_territories.should_use_einvoicing('FR', 'FR'))

    def test_should_use_einvoicing_metro_to_drom_einvoicing(self):
        """Test: Metro ↔ DROM e-invoicing zones = E-invoicing."""
        # Metro -> DROM e-invoicing
        self.assertTrue(drom_com_territories.should_use_einvoicing('FR', 'GP'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('FR', 'MQ'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('FR', 'RE'))

        # DROM e-invoicing -> Metro
        self.assertTrue(drom_com_territories.should_use_einvoicing('GP', 'FR'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('MQ', 'FR'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('RE', 'FR'))

    def test_should_use_einvoicing_drom_to_drom_einvoicing(self):
        """Test: DROM e-invoicing ↔ DROM e-invoicing = E-invoicing."""
        self.assertTrue(drom_com_territories.should_use_einvoicing('GP', 'MQ'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('MQ', 'RE'))
        self.assertTrue(drom_com_territories.should_use_einvoicing('GP', 'RE'))

    def test_should_use_ereporting_metro_to_drom_ereporting(self):
        """Test: Metro ↔ DROM e-reporting = E-reporting (NOT e-invoicing)."""
        # Metro -> Guyane/Mayotte
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'GF'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'YT'))

        # Guyane/Mayotte -> Metro
        self.assertFalse(drom_com_territories.should_use_einvoicing('GF', 'FR'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('YT', 'FR'))

    def test_should_use_ereporting_metro_to_com(self):
        """Test: Metro ↔ COM = E-reporting (NOT e-invoicing)."""
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'BL'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'NC'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'PF'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('BL', 'FR'))

    def test_should_use_ereporting_drom_einvoicing_to_com(self):
        """Test: DROM e-invoicing ↔ COM = E-reporting."""
        self.assertFalse(drom_com_territories.should_use_einvoicing('GP', 'NC'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('MQ', 'PF'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('NC', 'GP'))

    def test_should_use_ereporting_international(self):
        """Test: France ↔ Foreign = E-reporting (NOT e-invoicing)."""
        self.assertFalse(drom_com_territories.should_use_einvoicing('FR', 'DE'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('GP', 'BE'))
        self.assertFalse(drom_com_territories.should_use_einvoicing('DE', 'FR'))

    # -------------------------------------------------------------------------
    # Test Transaction Flow Type Classification
    # -------------------------------------------------------------------------

    def test_transaction_type_b2c(self):
        """Test: No VAT = B2C transaction."""
        # No VAT
        self.assertEqual(drom_com_territories.get_transaction_flow_type('FR', 'FR', None), 'b2c')
        self.assertEqual(drom_com_territories.get_transaction_flow_type('FR', 'FR', ''), 'b2c')
        self.assertEqual(drom_com_territories.get_transaction_flow_type('FR', 'FR', '/'), 'b2c')

        # B2C in DROM-COM context
        self.assertEqual(drom_com_territories.get_transaction_flow_type('FR', 'GP', None), 'b2c')
        self.assertEqual(drom_com_territories.get_transaction_flow_type('GP', 'FR', '/'), 'b2c')

    def test_transaction_type_domestic_b2b_excluded(self):
        """Test: Domestic B2B in e-invoicing zones = False (excluded from Flux 10)."""
        # Metro -> Metro with VAT
        self.assertFalse(drom_com_territories.get_transaction_flow_type('FR', 'FR', 'FR12345678901'))

        # Metro -> DROM e-invoicing with VAT
        self.assertFalse(drom_com_territories.get_transaction_flow_type('FR', 'GP', 'FR98765432109'))
        self.assertFalse(drom_com_territories.get_transaction_flow_type('FR', 'MQ', 'FR11111111111'))

        # DROM e-invoicing -> DROM e-invoicing with VAT
        self.assertFalse(drom_com_territories.get_transaction_flow_type('GP', 'MQ', 'FR22222222222'))
        self.assertFalse(drom_com_territories.get_transaction_flow_type('RE', 'GP', 'FR33333333333'))

    def test_transaction_type_international_true_international(self):
        """Test: True international B2B = 'international' (in Flux 10)."""
        # France -> Foreign country
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'DE', 'DE123456789'),
            'international'
        )
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'BE', 'BE0123456789'),
            'international'
        )

        # DROM -> Foreign country
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('GP', 'ES', 'ESA12345678'),
            'international'
        )

    def test_transaction_type_international_drom_ereporting(self):
        """Test: Transactions with DROM e-reporting zones = 'international' (in Flux 10)."""
        # Metro -> Guyane/Mayotte
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'GF', 'FR12345678901'),
            'international'
        )
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'YT', 'FR98765432109'),
            'international'
        )

        # Guyane/Mayotte -> Metro
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('GF', 'FR', 'FR11111111111'),
            'international'
        )

        # DROM e-invoicing -> Guyane/Mayotte
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('GP', 'GF', 'FR22222222222'),
            'international'
        )

    def test_transaction_type_international_com(self):
        """Test: Transactions with COM territories = 'international' (in Flux 10)."""
        # Metro -> COM
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'BL', 'FR12345678901'),
            'international'
        )
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'NC', 'FR98765432109'),
            'international'
        )
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('FR', 'PF', 'FR11111111111'),
            'international'
        )

        # COM -> Metro
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('BL', 'FR', 'FR22222222222'),
            'international'
        )

        # DROM -> COM
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('GP', 'NC', 'FR33333333333'),
            'international'
        )

        # COM -> COM
        self.assertEqual(
            drom_com_territories.get_transaction_flow_type('BL', 'NC', 'FR44444444444'),
            'international'
        )

    # -------------------------------------------------------------------------
    # Test Country Code Mapping for PPF
    # -------------------------------------------------------------------------

    def test_map_country_code_for_ppf(self):
        """Test mapping of DROM-COM codes to FR for PPF transmission."""
        # DROM codes should map to FR
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('GP'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('MQ'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('RE'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('GF'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('YT'), 'FR')

        # COM codes should map to FR
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('BL'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('MF'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('PM'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('WF'), 'FR')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('TF'), 'FR')

        # Metro France stays FR
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('FR'), 'FR')

        # Foreign countries stay unchanged
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('DE'), 'DE')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('BE'), 'BE')
        self.assertEqual(drom_com_territories.map_country_code_for_ppf('US'), 'US')

        # Edge cases
        self.assertEqual(drom_com_territories.map_country_code_for_ppf(''), '')
        self.assertIsNone(drom_com_territories.map_country_code_for_ppf(None))

    # -------------------------------------------------------------------------
    # Test Specific Identifier Schemes
    # -------------------------------------------------------------------------

    def test_get_specific_identifier_scheme(self):
        """Test retrieval of specific identifier schemes for territories."""
        # New Caledonia - RIDET
        scheme = drom_com_territories.get_specific_identifier_scheme('NC')
        self.assertIsNotNone(scheme)
        self.assertEqual(scheme['qualifier'], '0228')
        self.assertEqual(scheme['name'], 'RIDET')

        # French Polynesia - TAHITI
        scheme = drom_com_territories.get_specific_identifier_scheme('PF')
        self.assertIsNotNone(scheme)
        self.assertEqual(scheme['qualifier'], '0229')
        self.assertEqual(scheme['name'], 'TAHITI')

        # Wallis & Futuna
        scheme = drom_com_territories.get_specific_identifier_scheme('WF')
        self.assertIsNotNone(scheme)
        self.assertEqual(scheme['qualifier'], '0227')

        # Territories without specific schemes
        self.assertIsNone(drom_com_territories.get_specific_identifier_scheme('GP'))
        self.assertIsNone(drom_com_territories.get_specific_identifier_scheme('FR'))
        self.assertIsNone(drom_com_territories.get_specific_identifier_scheme('DE'))

    # -------------------------------------------------------------------------
    # Test Helper Functions
    # -------------------------------------------------------------------------

    def test_is_b2b_transaction(self):
        """Test B2B detection based on VAT presence."""
        # B2B - has VAT
        self.assertTrue(drom_com_territories.is_b2b_transaction('FR12345678901'))
        self.assertTrue(drom_com_territories.is_b2b_transaction('DE123456789'))

        # B2C - no VAT
        self.assertFalse(drom_com_territories.is_b2b_transaction(None))
        self.assertFalse(drom_com_territories.is_b2b_transaction(''))
        self.assertFalse(drom_com_territories.is_b2b_transaction('/'))

    def test_get_drom_com_info(self):
        """Test comprehensive territory information retrieval."""
        info = drom_com_territories.get_drom_com_info()

        # Verify structure for key territories
        self.assertIn('GP', info)
        self.assertEqual(info['GP']['type'], 'drom_einvoicing')
        self.assertEqual(info['GP']['vat_regime'], 'similar_to_metro')

        self.assertIn('GF', info)
        self.assertEqual(info['GF']['type'], 'drom_ereporting')
        self.assertEqual(info['GF']['vat_regime'], 'specific_export')

        self.assertIn('NC', info)
        self.assertEqual(info['NC']['type'], 'com')
        self.assertEqual(info['NC']['vat_regime'], 'non_domestic')
        self.assertEqual(info['NC']['identifier'], 'RIDET')

        self.assertIn('PF', info)
        self.assertEqual(info['PF']['identifier'], 'TAHITI')

        self.assertIn('FR', info)
        self.assertEqual(info['FR']['type'], 'metro')
