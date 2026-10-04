from odoo import models

CTA_PRIORITY_TEST = 999


class Website(models.Model):
    _inherit = 'website'

    def _get_cta_candidates(self, website_type):
        candidates = super()._get_cta_candidates(website_type)
        candidates.append((CTA_PRIORITY_TEST, {
            'cta_btn_text': self.with_context(lang=self.default_lang_id.code).env._("Test CTA"),
            'cta_btn_href': '/test_cta',
        }))
        return candidates
