# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install', 'bso')
class TestTranslation(HttpCase):
    
    def single_language(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_single_language', login='admin')

    def multi_language(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_multi_language', login='admin')

    def fr_db(self):
        self.fr_en_db();
        lang_en = self.env.ref('base.lang_en')
        lang_en.active = False

    def fr_en_db(self):
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        self.env['res.lang']._activate_lang(lang_fr.code)
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
            website.language_ids -= lang_en
        for user in self.env['res.users'].search([]):
            user.lang = lang_fr.id
        for partner in self.env['res.partner'].search([]):
            partner.lang = lang_fr.id
        for user in self.env['res.users'].with_context(active_test=False).search([]):
            user.lang = lang_fr.id

    def en_fr_db(self):
        lang_fr = self.env.ref('base.lang_fr')
        self.env['res.lang']._activate_lang(lang_fr.code)

    def test_fr_db_fr_site(self):
        self.fr_db()
        self.single_language()

    def test_fr_en_db_fr_site(self):
        self.fr_en_db()
        self.single_language()

    def test_fr_en_db_en_site(self):
        self.fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
            website.default_lang_id = lang_en
            website.language_ids -= lang_fr
        self.single_language()

    def test_fr_en_db_fr_en_site(self):
        self.fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
        self.multi_language()

    def test_fr_en_db_en_fr_site(self):
        self.fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
            website.default_lang_id = lang_en
        self.multi_language()

    def test_en_fr_db_fr_site(self):
        self.en_fr_db()
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
            website.language_ids -= lang_en
        self.single_language()

    def test_en_fr_db_fr_en_site(self):
        self.en_fr_db()
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
        self.multi_language()

    def test_en_fr_db_en_fr_site(self):
        self.en_fr_db()
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
        self.multi_language()
