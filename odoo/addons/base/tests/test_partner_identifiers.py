from odoo.tests import TransactionCase, tagged
from odoo.tools.partner_identifiers import TIN_METADATA


@tagged('post_install', '-at_install')
class TestPartnerIdentifiers(TransactionCase):

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

    def test_identifier_metadata_duns_other(self):
        """ International metadata exposed by the computed field (no country). """
        partner = self.env['res.partner'].create({'name': 'No Country Partner'})
        metadata = partner.available_additional_identifiers_metadata
        self.assertTrue(isinstance(metadata, dict))
        self.assertEqual(len(metadata), 3)
        # Check standard properties for international
        self.assertIn('DUNS', metadata)
        self.assertIn('EAN_GLN', metadata)
        self.assertIn('OTHER', metadata)

    def test_identifier_metadata_by_country(self):
        """ Specific country check """
        partner = self.env['res.partner'].create({
            'name': 'BE Metadata Partner',
            'country_id': self.env.ref('base.be').id,
        })
        metadata_keys = partner.available_additional_identifiers_metadata.keys()
        self.assertIn('BE_EN', metadata_keys)
        self.assertNotIn('BE_VAT', metadata_keys)

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
        with self.assertLogs('odoo.addons.base.models.res_partner', level='WARNING') as logger:
            partner = self.env['res.partner'].create({
                'name': 'Test Unknown Key',
                'country_id': self.env.ref('base.be').id,
                'additional_identifiers': {'UNKNOWN_KEY': '12345', 'BE_EN': '0477472701'},
            })
            self.assertIn('identifier UNKNOWN_KEY is not in supported identifiers.', logger.output[0])

        self.assertNotIn('UNKNOWN_KEY', partner.additional_identifiers or {})
        self.assertIn('BE_EN', partner.additional_identifiers or {})

    def test_tin_metadata(self):
        # Please, set a category on the Tax ID.
        # The most generic is the "TIN". VAT is typically EU, and GST is typically ex-Commonwealth countries.
        tin_categories = {'VAT', 'GST', 'TIN'}
        for key, metadata in TIN_METADATA.items():
            self.assertIn('category', metadata)
            self.assertIn(metadata['category'], tin_categories)
            self.assertTrue(metadata['countries'])

    def test_no_dup_keys(self):
        """ Ensure no duplicate keys in the metadata dicts. """
        all_keys = set()
        for key in self.env['res.partner']._get_all_identifiers_metadata():
            self.assertNotIn(key, all_keys, f"Key {key} already exists in metadata")
            all_keys.add(key)

    def test_no_empty_str(self):
        # Don't leave empty values
        for identifier_name, metadata in self.env['res.partner']._get_all_identifiers_metadata().items():
            for key, value in metadata.items():
                self.assertNotEqual(value, '', f"Value for key {key} is empty for identifier {identifier_name}")

    def test_allowed_metadata_keys(self):
        # Ensure that we don't have any other keys than the allowed ones
        allowed_keys = {
            'category',
            'countries',
            'display_optional',
            'examples',
            'format',
            'help',
            'label',
            'placeholder',
            'scheme',
            'sequence',
            'synced',
            'validation_function',
        }
        for identifier_name, metadata in self.env['res.partner']._get_all_identifiers_metadata().items():
            for key in metadata:
                self.assertIn(key, allowed_keys, f"Key '{key}' is not in allowed keys for identifier {identifier_name}")
                if key == 'countries':
                    # False is ok but must be explicitly stated
                    self.assertTrue(metadata[key] is not None, f"Countries must be set for identifier {key}")
                    self.assertTrue(isinstance(metadata[key], list) if metadata[key] else True, f"Value for key '{key}' is not a list or None for identifier {identifier_name}")
                if key == 'display_optional':
                    self.assertIn(metadata[key], ['show', 'hide', None], f"Value for key '{key}' is not in ['show', 'hide', None] for identifier {identifier_name}")
                if key == 'synced':
                    self.assertTrue(isinstance(metadata[key], bool), f"Value for key '{key}' is not a boolean for identifier {identifier_name}")

    def test_tin_metadata_single_entry_per_country(self):
        """ ``get_tin_metadata_of_country`` assumes a single tax ID per country, so each
        country must appear in at most one ``TIN_METADATA`` entry.
        """
        entries_per_country = {}
        for key, metadata in TIN_METADATA.items():
            for country in (metadata.get('countries') or []):
                entries_per_country.setdefault(country, []).append(key)
        duplicates = {country: keys for country, keys in entries_per_country.items() if len(keys) > 1}
        self.assertFalse(
            duplicates,
            "Each country must have a single TIN_METADATA entry, found duplicates: %s" % duplicates,
        )
