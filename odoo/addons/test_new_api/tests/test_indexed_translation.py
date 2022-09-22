# -*- coding: utf-8 -*-

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestIndexedTranslation(odoo.tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.record_en = cls.env['test_new_api.indexed_translation'].with_context(lang='en_US').create({})
        cls.record_fr = cls.record_en.with_context(lang='fr_FR')
        cls.record_en.name = '<div class="my_class">hello</div>\n<div/>'
        cls.record_fr.name = '<div class="my_class">%bonjour\\</div>\a<div/>'

    def test_search_ilike(self):
        self.assertEqual(self.record_en.name, '<div class="my_class">hello</div>\n<div/>')
        self.assertEqual(self.record_fr.name, '<div class="my_class">%bonjour\\</div>\a<div/>')

        # matching double quotes
        self.assertEqual(self.record_en.search([('name', 'ilike', 'class="my_class')]), self.record_en)

        # escaped and unescaped PG wildcards
        self.assertEqual(self.record_en.search([('name', 'ilike', 'class%class')]), self.record_en)
        self.assertEqual(self.record_en.search([('name', 'ilike', r'class="m_\_class')]), self.record_en)
        self.assertEqual(self.record_en.search([('name', 'ilike', 'bonjour')]), self.record_en.browse())
        self.assertEqual(self.record_en.search([('name', 'ilike', '</div>\n<div/>')]), self.record_en)
        self.assertEqual(self.record_fr.search([('name', 'ilike', '</div>\a<div/>')]), self.record_fr)
        self.assertEqual(self.record_fr.search([('name', 'ilike', r'\%bonjour\\')]), self.record_fr)

        self.assertEqual(
            self.record_en.search([('name', '=', '<div class="my_class">hello</div>\n<div/>')]),
            self.record_en,
        )
        self.assertEqual(
            self.record_fr.search([('name', '=', '<div class="my_class">%bonjour\\</div>\a<div/>')]),
            self.record_fr,
        )
