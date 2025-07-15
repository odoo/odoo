# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestTranslationOverride(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['res.partner.category'].create({'name': 'Reblochon'})
        cls.custom = cls.env['ir.model.fields'].create({
            'name': 'x_html_test',
            'ttype': 'html',
            'model_id': cls.category.id,
            'translate': 'html_translate',
        })

    def test_web_override_translations(self):
        self.env['res.lang']._activate_lang('fr_FR')
        categoryEN = self.category.with_context(lang='en_US')
        categoryFR = self.category.with_context(lang='fr_FR')
        customEN = self.custom.with_context(lang='en_US')
        customFR = self.custom.with_context(lang='fr_FR')

        self.category.web_override_translations({'name': 'commonName'})
        self.assertEqual(categoryEN.name, 'commonName')
        self.assertEqual(categoryFR.name, 'commonName')

        # cannot void translations (incluiding en_US)
        self.category.web_override_translations({'name': False})
        self.assertEqual(categoryEN.name, 'commonName')
        self.assertEqual(categoryFR.name, 'commonName')

        # empty str is a valid translation
        self.category.web_override_translations({'name': ''})
        self.assertEqual(categoryEN.name, '')
        self.assertEqual(categoryFR.name, '')

        # translated html fields are not changed
        self.custom.web_override_translations({'name': '<div>dont</div><div>change</div>'})
        self.assertEqual(customEN.name, 'x_html_test')
        self.assertEqual(customFR.name, 'x_html_test')
