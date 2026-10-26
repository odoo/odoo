# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestWebsitePartnerSeo(TransactionCase):

    def test_user_meta_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        user = new_test_user(self.env, 'seo_user')
        user.partner_id.website_meta_description = 'Description'
        user.partner_id.with_context(lang='fr_FR').website_meta_description = 'Description FR'
        # the translations are read in SQL
        self.env.flush_all()
        self.assertEqual(user.get_website_meta_i18n_value('website_meta_description', 'fr_FR'), 'Description FR')
