# -*- coding: utf-8 -*-

from contextlib import closing
import base64
import io

import odoo
from odoo.tests import common, tagged
from odoo.tools.misc import file_open, mute_logger
from odoo.tools.translate import _, _lt, TranslationFileReader, TranslationModuleReader
from odoo import Command


class TestImport(common.TransactionCase):

    def test_import_code_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')

        # Code translation in the current implementation doesn't need to be imported manually.
        # odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        self.assertEqual(
            self.env['test.translation.import.model1'].with_context(lang='fr_FR').get_code_translation(),
            'Code, Français'
        )

    def test_import_model_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_FR').name,
            'Vaisselle'
        )

    def test_import_model_term_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_FR').xml,
            '<form string="Fourchette"><div>Couteau</div><div>Cuillère</div></form>'
        )

    def test_noupdate(self):
        """
        Make sure no update do not overwrite translations
        """
        menu = self.env.ref('test_translation_import.menu_test_translation_import')
        self.assertEqual(menu.name, 'Test translation model1')
        # install french and change translation content
        self.env['res.lang']._activate_lang('fr_FR')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Test translation import in french")
        menu.with_context(lang='fr_FR').name = "Nouveau nom"
        # reload with overwrite
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False, overwrite=True)

        # TODO CWG: recheck
        # trans_load invalidates ormcache but not record cache
        # self.env.invalidate_all()
        self.assertEqual(menu.name, "Test translation model1")
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom")

    def test_lang_with_base(self):
        self.env['res.lang']._activate_lang('fr_BE')
        self.env['res.lang']._activate_lang('fr_CA')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_BE', verbose=False)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr_BE.po', 'fr_BE', verbose=False, overwrite=True)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_CA', verbose=False)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr_CA.po', 'fr_CA', verbose=False, overwrite=True)

        # language override base language
        self.assertEqual(
            self.env['test.translation.import.model1'].with_context(lang='fr_BE').get_code_translation(),
            'Code, Français, Belgium'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_BE').name,
            'Vaisselle, Belgium'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_BE').xml,
            '<form string="Fourchette, Belgium"><div>Couteau, Belgium</div><div>Cuillère, Belgium</div></form>'
        )

        # not specified localized language fallback on base language
        self.assertEqual(
            self.env['test.translation.import.model1'].with_context(lang='fr_CA').get_code_translation(),
            'Code, Français'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_CA').name,
            'Vaisselle'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='fr_CA').xml,
            '<form string="Fourchette"><div>Couteau, Canada</div><div>Cuillère</div></form>'
        )

    # TODO CWG: recheck
    # def test_export_empty_string(self):
    #     """When the string and the translation is equal the translation is empty"""
    #     # Export the translations
    #     def update_translations(create_empty_translation=False):
    #         self.env['res.lang']._activate_lang('fr_FR')
    #         with closing(io.BytesIO()) as bufferobj:
    #             odoo.tools.trans_export('fr_FR', ['test_translation_import'], bufferobj, 'po', self.cr)
    #             bufferobj.name = 'test_translation_import/i18n/fr.po'
    #             odoo.tools.trans_load_data(self.cr, bufferobj, 'po', 'fr_FR',
    #                                        verbose=False,
    #                                        create_empty_translation=create_empty_translation,
    #                                        overwrite=True)
    #
    #     # Check that the not translated key is not created
    #     update_translations()
    #     translation = self.env['ir.translation'].search_count([('src', '=', 'Efgh'), ('value', '=', '')])
    #     self.assertFalse(translation, 'An empty translation is not imported')
    #
    #     # Check that "Generate Missing Terms" create empty string for not translated key
    #     update_translations(create_empty_translation=True)
    #     translation = self.env['ir.translation'].search_count([('src', '=', 'Efgh'), ('value', '=', '')])
    #     self.assertTrue(translation, 'The translation of "Efgh" should be empty')
    #
    #     # Modify the value translated for the equal value of the key
    #     menu = self.env.ref('test_translation_import.menu_test_translation_import')
    #     menu.name = "New Name"
    #     menu.with_context(lang='fr_FR').name = "New Name"
    #     update_translations()
    #     self.assertEqual(menu.with_context(lang='fr_FR').name, "New Name", 'The translation of "New Name" should be "New Name"')
    #
    #     # Modify the value translated for another different value
    #     menu.name = "New Name"
    #     menu.with_context(lang='fr_FR').name = "Nouveau nom"
    #     update_translations()
    #     self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom", 'The translation of "New Name" should be "Nouveau nom"')

    def test_import_from_po_file(self):
        """Test the import from a single po file works"""
        with file_open('test_translation_import/i18n/tlh.po', 'rb') as f:
            po_file = base64.encodebytes(f.read())

        import_tlh = self.env["base.language.import"].create({
            'name': 'Klingon',
            'code': 'tlh',
            'data': po_file,
            'filename': 'tlh.po',
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_tlh.import_lang()

        tlh_lang = self.env['res.lang']._lang_get('tlh')
        self.assertTrue(tlh_lang, "The imported language was not creates")

        self.assertEqual(
            self.env['test.translation.import.model1'].with_context(lang='tlh').get_code_translation(),
            'Code, Klingon'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='tlh').name,
            'Tableware, Klingon'
        )

    def test_lazy_translation(self):
        """Test the import from a single po file works"""
        with file_open('test_translation_import/i18n/tlh.po', 'rb') as f:
            po_file = base64.encodebytes(f.read())

        import_tlh = self.env["base.language.import"].create({
            'name': 'Klingon',
            'code': 'tlh',
            'data': po_file,
            'filename': 'tlh.po',
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_tlh.import_lang()

        TestTranslationImportModel1 = self.env['test.translation.import.model1']
        TRANSLATED_TERM = TestTranslationImportModel1.get_code_lazy_translation()

        self.assertEqual(
            TestTranslationImportModel1.with_context(lang='tlh').get_code_translation(),
            "Code, Klingon",
            "The direct code translation was not applied"
        )
        context = None

        # Comparison of lazy strings must be explicitely casted to string
        with self.assertRaises(NotImplementedError):
            TRANSLATED_TERM == "Code, English"
        self.assertEqual(str(TRANSLATED_TERM), "Code Lazy, English", "The translation should not be applied yet")

        context = {'lang': "tlh"}
        self.assertEqual(str(TRANSLATED_TERM), "Code Lazy, Klingon", "The lazy code translation was not applied")

        self.assertEqual("Do you speak " + TRANSLATED_TERM, "Do you speak Code Lazy, Klingon", "str + _lt concatenation failed")
        self.assertEqual(TRANSLATED_TERM + ", I speak it", "Code Lazy, Klingon, I speak it", "_lt + str concatenation failed")
        self.assertEqual(TRANSLATED_TERM + TRANSLATED_TERM, "Code Lazy, KlingonCode Lazy, Klingon", "_lt + _lt concatenation failed")

    def test_import_from_csv_file(self):
        """Test the import from a single CSV file works"""
        with file_open('test_translation_import/i18n/dot.csv', 'rb') as f:
            po_file = base64.encodebytes(f.read())

        import_tlh = self.env["base.language.import"].create({
            'name': 'Dothraki',
            'code': 'dot',
            'data': po_file,
            'filename': 'dot.csv',
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_tlh.import_lang()

        dot_lang = self.env['res.lang']._lang_get('dot')
        self.assertTrue(dot_lang, "The imported language was not creates")

        # code translation cannot be changed or imported, it only depends on the po file in the module directory
        self.assertEqual(
            self.env['test.translation.import.model1'].with_context(lang='dot').get_code_translation(),
            'Code, English'
        )
        self.assertEqual(
            self.env.ref('test_translation_import.test_translation_import_model1_record1').with_context(lang='dot').name,
            'Tableware, Dot'
        )

    def test_translation_placeholder(self):
        """Verify placeholder use in _()"""
        self.env['res.lang']._activate_lang('fr_BE')

        TestTranslationImportModel1_BE = self.env['test.translation.import.model1'].with_context(lang='fr_BE')

        # correctly translate
        self.assertEqual(
            TestTranslationImportModel1_BE.get_code_placeholder_translation(1),
            "Code, 1, Français, Belgium",
            "Translation placeholders were not applied"
        )

        # source error: wrong arguments
        with self.assertRaises(TypeError), self.cr.savepoint():
            TestTranslationImportModel1_BE.get_code_placeholder_translation(1, "🧀")

        # correctly translate
        self.assertEqual(
            TestTranslationImportModel1_BE.get_code_named_placeholder_translation(num=2, symbol="🧀"),
            "Code, 2, 🧀, Français, Belgium",
            "Translation placeholders were not applied"
        )

        # source error: wrong arguments
        with self.assertRaises(KeyError), self.cr.savepoint():
            TestTranslationImportModel1_BE.get_code_named_placeholder_translation(symbol="🧀"),


@tagged('post_install', '-at_install')
class TestTranslationFlow(common.TransactionCase):

    def test_export_import(self):
        """ Ensure export+import gives the same result as loading a language """
        # load language and generate missing terms to create missing empty terms
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [self.env.ref('base.lang_fr').id])],
        }).lang_install()

        self.env["base.update.translations"].create({'lang': 'fr_FR'}).act_update()

        module = self.env.ref('base.module_test_translation_import')
        export = self.env["base.language.export"].create({
            'lang': 'fr_FR',
            'format': 'po',
            'modules': [Command.set([module.id])]
        })
        export.act_getfile()
        po_file = export.data
        self.assertIsNotNone(po_file)

        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='fr_FR').name,
            'Vaisselle'
        )
        self.assertEqual(
            record.with_context(lang='fr_FR').xml,
            '<form string="Fourchette"><div>Couteau</div><div>Cuillère</div></form>'
        )

        # remove All translations
        record.name = ''
        record.name = 'Tableware'
        record.xml = ''
        record.xml = '<form string="Fork"><div>Knife</div><div>Spoon</div></form>'
        self.assertEqual(
            record.with_context(lang='fr_FR').name,
            'Tableware'
        )
        self.assertEqual(
            record.with_context(lang='fr_FR').xml,
            '<form string="Fork"><div>Knife</div><div>Spoon</div></form>'
        )

        import_fr = self.env["base.language.import"].create({
            'name': 'French',
            'code': 'fr_FR',
            'data': export.data,
            'filename': export.name,
            'overwrite': False,
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_fr.import_lang()

        self.assertEqual(
            record.with_context(lang='fr_FR').name,
            'Vaisselle'
        )
        self.assertEqual(
            record.with_context(lang='fr_FR').xml,
            '<form string="Fourchette"><div>Couteau</div><div>Cuillère</div></form>'
        )

    def test_export_import_csv(self):
        """ Ensure can reimport exported csv """
        self.env.ref("base.lang_fr").active = True

        module = self.env.ref('base.module_test_translation_import')
        export = self.env["base.language.export"].create({
            'lang': 'fr_FR',
            'format': 'csv',
            'modules': [Command.set([module.id])]
        })
        export.act_getfile()
        po_file = export.data
        self.assertIsNotNone(po_file)

        import_fr = self.env["base.language.import"].create({
            'name': 'French',
            'code': 'fr_FR',
            'data': export.data,
            'filename': export.name,
            'overwrite': False,
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_fr.with_context().import_lang()

    def test_export_static_templates(self):
        trans_static = []
        po_reader = TranslationModuleReader(self.env.cr, ['test_translation_import'])
        for line in po_reader:
            module, ttype, name, res_id, source, value, comments = line
            if name == "addons/test_translation_import/static/src/xml/js_templates.xml":
                trans_static.append(source)

        self.assertNotIn('no export', trans_static)
        self.assertIn('do export', trans_static)
        self.assertIn('text node', trans_static)
        self.assertIn('slot', trans_static)
        self.assertIn('slot 2', trans_static)
