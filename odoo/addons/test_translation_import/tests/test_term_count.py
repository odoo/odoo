# -*- coding: utf-8 -*-

from contextlib import closing
import base64
import io

import odoo
from odoo.tests import common, tagged
from odoo.tools.misc import file_open, mute_logger
from odoo.tools.translate import _, _lt, TranslationFileReader, TranslationModuleReader
from odoo import Command
from odoo.addons.base.models.ir_fields import BOOLEAN_TRANSLATIONS


class TestImport(common.TransactionCase):

    def test_import_code_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')

        # Tip: code translations don't need to be imported explicitly
        # odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        model = self.env['test.translation.import.model1']
        self.assertEqual(
            model.with_context(lang='fr_FR').get_code_translation(),
            'Code, Français'
        )

    def test_import_model_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='fr_FR').name,
            'Vaisselle'
        )

    def test_import_model_term_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)

        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='fr_FR').xml,
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
        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='fr_BE').get_code_translation(),
            'Code, Français, Belgium'
        )
        self.assertEqual(
            record.with_context(lang='fr_BE').name,
            'Vaisselle, Belgium'
        )
        self.assertEqual(
            record.with_context(lang='fr_BE').xml,
            '<form string="Fourchette, Belgium"><div>Couteau, Belgium</div><div>Cuillère, Belgium</div></form>'
        )

        # not specified localized language fallback on base language
        self.assertEqual(
            record.with_context(lang='fr_CA').get_code_translation(),
            'Code, Français'
        )
        self.assertEqual(
            record.with_context(lang='fr_CA').name,
            'Vaisselle'
        )
        self.assertEqual(
            record.with_context(lang='fr_CA').xml,
            '<form string="Fourchette"><div>Couteau, Canada</div><div>Cuillère</div></form>'
        )

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

        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='tlh').get_code_translation(),
            'Code, Klingon'
        )
        self.assertEqual(
            record.with_context(lang='tlh').name,
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

        model = self.env['test.translation.import.model1']
        TRANSLATED_TERM = model.get_code_lazy_translation()

        self.assertEqual(
            model.with_context(lang='tlh').get_code_translation(),
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

        # test lazy translation in another module
        self.env['res.lang']._activate_lang('fr_FR')
        context = {'lang': 'en_US'}
        self.assertEqual(str(BOOLEAN_TRANSLATIONS[0]), 'yes')
        context = {'lang': 'fr_FR'}
        self.assertEqual(str(BOOLEAN_TRANSLATIONS[0]), 'oui')

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
        record = self.env.ref('test_translation_import.test_translation_import_model1_record1')
        self.assertEqual(
            record.with_context(lang='dot').get_code_translation(),
            'Code, English'
        )
        self.assertEqual(
            record.with_context(lang='dot').name,
            'Tableware, Dot'
        )

    def test_translation_placeholder(self):
        """Verify placeholder use in _()"""
        self.env['res.lang']._activate_lang('fr_BE')

        model_fr_BE = self.env['test.translation.import.model1'].with_context(lang='fr_BE')

        # correctly translate
        self.assertEqual(
            model_fr_BE.get_code_placeholder_translation(1),
            "Code, 1, Français, Belgium",
            "Translation placeholders were not applied"
        )

        # source error: wrong arguments
        with self.assertRaises(TypeError):
            model_fr_BE.get_code_placeholder_translation(1, "🧀")

        # correctly translate
        self.assertEqual(
            model_fr_BE.get_code_named_placeholder_translation(num=2, symbol="🧀"),
            "Code, 2, 🧀, Français, Belgium",
            "Translation placeholders were not applied"
        )

        # source error: wrong arguments
        with self.assertRaises(KeyError):
            model_fr_BE.get_code_named_placeholder_translation(symbol="🧀"),


@tagged('post_install', '-at_install')
class TestTranslationFlow(common.TransactionCase):

    def test_export_import(self):
        """ Ensure export+import gives the same result as loading a language """
        # load language and generate missing terms to create missing empty terms
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [self.env.ref('base.lang_fr').id])],
        }).lang_install()

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
        record.invalidate_recordset()
        self.assertEqual(
            record.with_context(lang='fr_FR').name,
            'Vaisselle'
        )
        self.assertEqual(
            record.with_context(lang='fr_FR').xml,
            '<form string="Fourchette"><div>Couteau</div><div>Cuillère</div></form>'
        )

        # remove All translations
        record.name = False
        record.name = 'Tableware'
        record.xml = False
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

    def test_export_spreadsheet(self):
        terms = []
        po_reader = TranslationModuleReader(self.env.cr, ['test_translation_import'])
        for line in po_reader:
            _module, _ttype, name, _res_id, source, _value, _comments = line
            if name == "addons/test_translation_import/data/files/test_spreadsheet_dashboard.json":
                terms.append(source)
        self.assertEqual(set(terms), {
            'exported 1',
            'exported 2',
            'exported 3',
            'Bar chart title',
            'Scorecard description',
            'Scorecard chart',
            'Opportunities',
            'Pipeline',
            'Pipeline Analysis',
            'link label',
            'aa (\\"inside\\") bb',
            'with spaces',
            'hello \\"world\\"',
        })
