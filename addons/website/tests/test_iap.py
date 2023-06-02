# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests
from odoo.addons.iap.tools import iap_tools

@odoo.tests.tagged('external')
class TestIap(odoo.tests.HttpCase):

    def test_01_industries_lang(self):
        """Ensure that the industries are translated in all the languages
        supported by the configurator."""
        def _get_industries(lang):
            industries = self.env['website']._website_api_rpc('/api/website/1/configurator/industries', {'lang': lang})['industries']
            return {industry['id']: industry['label'] for industry in industries}

        with iap_tools.enable_iap_test():
            english_terms = _get_industries('en')
            # Check that every languages are different from english.
            for lang in ['de', 'es', 'fr', 'hr', 'hu', 'id', 'it', 'mk', 'nl', 'pt', 'ru', 'zh']:
                translated_terms = _get_industries(lang)
                has_diff = False
                self.assertEqual(len(english_terms), len(translated_terms), "Different number of industries between 'en' and %s" % lang)
                for industry_id, english_label in english_terms.items():
                    translated_label = translated_terms.get(industry_id, False)
                    self.assertTrue(translated_label, "Industry %s is not in %s" % (english_label, lang))
                    if english_label != translated_label:
                        # One difference is enough to consider the translation
                        # as valid.
                        has_diff = True
                        break
                self.assertTrue(has_diff, "No difference found between 'en' and %s" % lang)
