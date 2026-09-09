from unittest.mock import patch

import odoo.tests
from odoo import modules
from odoo.exceptions import AccessError


@odoo.tests.tagged("website_nightly", "-standard")
class TestIap(odoo.tests.HttpCase):
    def test_01_industries_lang(self):
        def _get_industries(lang):
            with patch.object(modules.module, "current_test", False):
                industries = self.env["website"]._website_api_rpc(
                    "/api/website/1/configurator/industries", {"lang": lang}
                )["industries"]
            return {industry["id"]: industry["label"] for industry in industries}

        try:
            english_terms = _get_industries("en")
        except AccessError as e:
            # The IAP endpoint being unreachable/erroring out is an
            # environment issue, not a translation regression: don't let it
            # masquerade as one.
            self.skipTest(f"IAP industries endpoint unavailable: {e}")
        for lang in [
            "ar",
            "de",
            "es",
            "fr",
            "hr",
            "hu",
            "id",
            "it",
            "mk",
            "nl",
            "pt",
            "ru",
            "zh",
        ]:
            try:
                translated_terms = _get_industries(lang)
            except AccessError as e:
                self.skipTest(f"IAP industries endpoint unavailable: {e}")
            has_diff = False
            self.assertEqual(
                len(english_terms),
                len(translated_terms),
                "Different number of industries between 'en' and %s" % lang,
            )
            for industry_id, english_label in english_terms.items():
                translated_label = translated_terms.get(industry_id, False)
                self.assertTrue(
                    translated_label, "Industry %s is not in %s" % (english_label, lang)
                )
                if english_label != translated_label:
                    has_diff = True
                    break
            self.assertTrue(has_diff, "No difference found between 'en' and %s" % lang)
