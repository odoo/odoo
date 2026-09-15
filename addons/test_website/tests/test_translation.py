# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest


@tagged('post_install', '-at_install', 'is_tour')
class TestTranslation(HttpCase):

    def _single_language_fr_user_fr_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_single_language_fr_user_fr_site', login='admin')

    def _single_language_en_user_fr_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_single_language_en_user_fr_site', login='admin')

    def _single_language_fr_user_en_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_single_language_fr_user_en_site', login='admin')

    def _multi_language_fr_user_fr_en_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_multi_language_fr_user_fr_en_site', login='admin', timeout=250)

    def _multi_language_fr_user_en_fr_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_multi_language_fr_user_en_fr_site', login='admin', timeout=250)

    def _multi_language_en_user_fr_en_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_multi_language_en_user_fr_en_site', login='admin', timeout=250)

    def _multi_language_en_user_en_fr_site(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'translation_multi_language_en_user_en_fr_site', login='admin', timeout=250)

    def _fr_db(self):
        self._fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        lang_en.active = False

    def _fr_en_db(self):
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [lang_fr.id])],
        }).lang_install()
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
            website.language_ids -= lang_en
        self.env['website'].create({
            'sequence': 1,
            'name': 'Test FR Website',
            'language_ids': [
                Command.link(lang_fr.id),
            ],
            'default_lang_id': lang_fr.id,
        })

        for user in self.env['res.users'].search([]):
            user.lang = lang_fr.code
        for partner in self.env['res.partner'].search([]):
            partner.lang = lang_fr.code
        for user in self.env['res.users'].with_context(active_test=False).search([]):
            user.lang = lang_fr.code

    def _en_fr_db(self):
        lang_fr = self.env.ref('base.lang_fr')
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [lang_fr.id])],
        }).lang_install()

    def test_fr_db_fr_site(self):
        self._fr_db()
        self._single_language_fr_user_fr_site()

    def test_fr_en_db_fr_site(self):
        self._fr_en_db()
        self._single_language_fr_user_fr_site()

    def test_fr_en_db_en_site(self):
        self._fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
            website.default_lang_id = lang_en
            website.language_ids -= lang_fr
        self._single_language_fr_user_en_site()

    def test_fr_en_db_fr_en_site(self):
        self._fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
        self._multi_language_fr_user_fr_en_site()

    def test_fr_en_db_en_fr_site(self):
        self._fr_en_db()
        lang_en = self.env.ref('base.lang_en')
        for website in self.env['website'].search([]):
            website.language_ids += lang_en
            website.default_lang_id = lang_en
        self._multi_language_fr_user_en_fr_site()

    def test_en_fr_db_fr_site(self):
        self._en_fr_db()
        lang_en = self.env.ref('base.lang_en')
        lang_fr = self.env.ref('base.lang_fr')
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [lang_fr.id])],
        }).lang_install()
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
            website.language_ids -= lang_en
        self._single_language_en_user_fr_site()

    def test_en_fr_db_fr_en_site(self):
        self._en_fr_db()
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
            website.default_lang_id = lang_fr
        self._multi_language_en_user_fr_en_site()

    def test_en_fr_db_en_fr_site(self):
        self._en_fr_db()
        lang_fr = self.env.ref('base.lang_fr')
        for website in self.env['website'].search([]):
            website.language_ids += lang_fr
        self._multi_language_en_user_en_fr_site()


@tagged('post_install', '-at_install')
class TestFieldTranslation(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['res.lang']._activate_lang('nl_NL')
        lang_fr = cls.env.ref('base.lang_fr')
        cls.website = cls.env['website'].create({
            'name': 'Test Website',
            'language_ids': [lang_fr.id],
            'default_lang_id': lang_fr.id,
        })

    def _test_translation_sequence(self, view, record_to_translate, view_record):
        def render_view_with_lang(lang):
            return view.with_context(edit_translations=True)._render_template(
                view.id, {'record': view_record.with_context(lang=lang), 'translatable': True},
            )

        with MockRequest(self.env, website=self.website):
            self.assertIn('translated', render_view_with_lang('fr_FR'))
            self.assertIn('to_translate', render_view_with_lang('en_US'))
            self.assertIn('to_translate', render_view_with_lang('nl_NL'))

        record_to_translate.update_field_translations('name', {'en_US': 'In English'})
        with MockRequest(self.env, website=self.website):
            self.assertIn('translated', render_view_with_lang('fr_FR'))
            self.assertIn('translated', render_view_with_lang('en_US'))
            self.assertIn('to_translate', render_view_with_lang('nl_NL'))

        record_to_translate.update_field_translations('name', {'nl_NL': 'In het Nederlands'})
        with MockRequest(self.env, website=self.website):
            self.assertIn('translated', render_view_with_lang('fr_FR'))
            self.assertIn('translated', render_view_with_lang('en_US'))
            self.assertIn('translated', render_view_with_lang('nl_NL'))

    def test_view_string_field_translation(self):
        record = self.env['test.model'].with_context(lang='fr_FR').create({
            'name': 'En Français',
        })
        view = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': """
                <div>
                    <span t-field="record.name"/>
                </div>
            """,
        })
        self._test_translation_sequence(view, record, record)

    def test_view_related_string_field_translation(self):
        record = self.env['test.model'].with_context(lang='fr_FR').create({
            'name': 'En Français',
        })
        sub_record = self.env['test.submodel'].create({
            'name': 'Subrecord', 'test_model_id': record.id,
        })
        view = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': """
                <div>
                    <span t-field="record.test_model_name"/>
                </div>
            """,
        })
        self._test_translation_sequence(view, record, sub_record)

    def test_view_deeply_related_string_field_translation(self):
        record = self.env['test.model'].with_context(lang='fr_FR').create({
            'name': 'En Français',
        })
        sub_record = self.env['test.submodel'].create({
            'name': 'Subrecord', 'test_model_id': record.id,
        })
        sub_sub_record = self.env['test.subsubmodel'].create({
            'test_submodel_id': sub_record.id,
        })
        view = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': """
                <div>
                    <span t-field="record.test_submodel_name"/>
                </div>
            """,
        })
        self._test_translation_sequence(view, record, sub_sub_record)
