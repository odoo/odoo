from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAdditionalIdentifiers(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner Identifiers',
            'country_id': cls.env.ref('base.fr').id,
        })

    def test_field_stores_json(self):
        """ Test that we can store and retrieve JSON from the new field. """
        self.partner.additional_identifiers = {'BE_EN': '0477472701'}
        self.assertEqual(self.partner.additional_identifiers, {'BE_EN': '0477472701'})

    def test_empty_value_not_stored(self):
        """ Test that empty string values are stripped before persistence. """
        self.partner.additional_identifiers = {'FR_SIRET': ''}
        self.assertFalse(self.partner.additional_identifiers)

    def test_mixed_empty_and_set_values(self):
        """ Test that empty strings are dropped while valid values remain. """
        self.partner.additional_identifiers = {'EAN_GLN': '9780471117094', 'FR_SIRET': ''}
        self.assertEqual(self.partner.additional_identifiers, {'EAN_GLN': '9780471117094'})
        self.assertNotIn('FR_SIRET', self.partner.additional_identifiers)

    def test_identifier_metadata_gln(self):
        """ Global metadata method call """
        metadata = self.env['res.partner'].get_available_additional_identifiers_metadata(None, seq_max=999)
        self.assertTrue(isinstance(metadata, dict))
        self.assertTrue(len(metadata) > 2)
        # Check standard properties for international
        gln_meta = metadata['EAN_GLN']
        self.assertEqual(gln_meta['scheme'], '0088')
        self.assertNotIn('type', gln_meta)

        self.assertNotIn('FR_VAT', metadata)  # Tax ids are excluded

    def test_identifier_proxy_gln(self):
        """ Test the "proxy" field (compute/inverse on the JSON) behavior. """
        self.partner.global_location_number = '9780471117094'
        self.assertEqual(self.partner.additional_identifiers, {'EAN_GLN': '9780471117094'})
        self.partner.global_location_number = False
        self.assertFalse(self.partner.additional_identifiers)

        self.partner._set_additional_identifier('EAN_GLN', '9780471117094')
        self.assertEqual(self.partner.additional_identifiers, {'EAN_GLN': '9780471117094'})
        self.partner.global_location_number = ''
        self.assertFalse(self.partner.additional_identifiers)

        with self.assertRaisesRegex(ValidationError, "Invalid identifier: EAN/GLN."):
            self.partner.global_location_number = 'wrong_gln'

    def test_identifier_metadata_by_country_multiple(self):
        """ Filters mapped directly to a country include generic and non-tax ids. """
        metadata = self.env['res.partner'].get_available_additional_identifiers_metadata('FR', seq_max=999)
        keys = metadata.keys()
        self.assertIn('FR_SIREN', keys)
        self.assertIn('FR_SIRET', keys)
        self.assertNotIn('FR_VAT', keys)

    def test_identifier_metadata_by_country(self):
        """ Specific country check """
        metadata = self.env['res.partner'].get_available_additional_identifiers_metadata('BE', seq_max=999)
        keys = metadata.keys()
        self.assertIn('BE_EN', keys)
        self.assertNotIn('BE_VAT', keys)

    def test_peppol_eas_metadata_keys(self):
        """ Check that essential non-tax EAS fallbacks are explicitly mapped. """
        metadata = self.env['res.partner'].get_available_additional_identifiers_metadata('NO', seq_max=999)
        keys_to_check = ['EAN_GLN', 'NO_EN']
        found_keys = [k for k in metadata if k in keys_to_check]
        self.assertEqual(len(found_keys), len(keys_to_check))

    def test_vat_deduces_additional_identifiers(self):
        """Setting a Belgian VAT should automatically deduce BE_EN (enterprise number)."""
        partner = self.env['res.partner'].create({
            'name': 'BE Partner',
            'country_id': self.env.ref('base.be').id,
        })
        partner.vat = 'BE0477472701'
        self.assertEqual(
            (partner.additional_identifiers or {}).get('BE_EN'),
            '0477472701',
            "BE_EN should be deduced from BE VAT by stripping the country prefix",
        )

    def test_vat_deduces_dk_cvr(self):
        """Setting a Danish VAT should automatically deduce DK_CVR."""
        partner = self.env['res.partner'].create({
            'name': 'DK Partner',
            'country_id': self.env.ref('base.dk').id,
        })
        partner.vat = 'DK12345674'
        self.assertEqual(
            (partner.additional_identifiers or {}).get('DK_CVR'),
            '12345674',
        )

    def test_vat_deduces_at_en(self):
        """Setting an Austrian VAT should automatically deduce AT_EN."""
        partner = self.env['res.partner'].create({
            'name': 'AT Partner',
            'country_id': self.env.ref('base.at').id,
        })
        partner.vat = 'ATU12345675'
        self.assertEqual(
            (partner.additional_identifiers or {}).get('AT_EN'),
            'U12345675',
        )

    def test_unknown_key_dropped(self):
        """Unknown identifier keys should be dropped on save with a logger warning."""
        with self.assertLogs('odoo.addons.account.models.partner', level='WARNING') as logger:
            partner = self.env['res.partner'].create({
                'name': 'Test Unknown Key',
                'country_id': self.env.ref('base.be').id,
                'additional_identifiers': {'UNKNOWN_KEY': '12345', 'BE_EN': '0477472701'},
            })
            self.assertIn('identifier UNKNOWN_KEY is not in supported identifiers.', logger.output[0])

        self.assertNotIn('UNKNOWN_KEY', partner.additional_identifiers or {})
        self.assertIn('BE_EN', partner.additional_identifiers or {})
