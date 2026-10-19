from odoo.modules import Manifest
from odoo.tests import TransactionCase


class TestLoadManifestTranslations(TransactionCase):
    def test_load_manifest_translations(self):
        manifest = Manifest.for_addon('test_translation', display_warning=False)
        translations_by_field = manifest.get_translations(['fr_FR', 'fr_BE', 'fr_CA', 'tlh', 'nl_NL'])

        self.assertEqual(
            translations_by_field['description'],
            {
                'fr_FR': 'Un module pour tester les traductions.',
                'fr_BE': 'Un module pour tester les traductions Belges.',
                'fr_CA': 'Un module pour tester les traductions.',
                'tlh': 'A module to test translation in Klingon.',
            },
        )
        self.assertEqual(
            translations_by_field['shortdesc'],
            {
                'fr_FR': 'Tester la traduction',
                'fr_BE': 'Tester la traduction',
                'fr_CA': 'Tester la traduction',
                'tlh': 'Test Translation in Klingon',
            },
        )
