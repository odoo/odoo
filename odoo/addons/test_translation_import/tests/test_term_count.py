# -*- coding: utf-8 -*-

from contextlib import closing
import base64
import io

import odoo
from odoo.tests import common, tagged
from odoo.tools.misc import file_open, mute_logger
from odoo.tools.translate import _, _lt, TranslationFileReader


TRANSLATED_TERM = _lt("Klingon")

class TestTermCount(common.TransactionCase):

    def test_count_term(self):
        """
        Just make sure we have as many translation entries as we wanted.
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
        translations = self.env['ir.translation'].search([
            ('lang', '=', 'fr_FR'),
            ('src', '=', '1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB'),
        ], order='type')
        self.assertEqual(len(translations), 2)
        self.assertEqual(translations[0].type, 'code')
        self.assertEqual(translations[0].module, 'test_translation_import')
        self.assertEqual(translations[0].name, 'addons/test_translation_import/models.py')
        self.assertEqual(translations[0].comments, '')
        self.assertEqual(translations[0].res_id, 15)
        self.assertEqual(translations[1].type, 'model')
        self.assertEqual(translations[1].module, 'test_translation_import')
        self.assertEqual(translations[1].name, 'ir.model.fields,field_description')
        self.assertEqual(translations[1].comments, '')
        field = self.env['ir.model.fields'].search([('model', '=', 'test.translation.import'), ('name', '=', 'name')])
        self.assertEqual(translations[1].res_id, field.id)

    def test_count_term_module(self):
        """
        Just make sure we have as many translation entries as we wanted and module deducted from file content
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)
        translations = self.env['ir.translation'].search([
            ('lang', '=', 'fr_FR'),
            ('src', '=', 'Ijkl'),
            ('module', '=', 'test_translation_import'),
        ])
        self.assertEqual(len(translations), 1)
        self.assertEqual(translations.res_id, 21)

    def test_noupdate(self):
        """
        Make sure no update do not overwrite translations
        """
        menu = self.env.ref('test_translation_import.menu_test_translation_import')
        menu.name = "New Name"
        # install french and change translation content
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
        menu.with_context(lang='fr_FR').name = "Nouveau nom"
        # reload with overwrite
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False, context={'overwrite': True})

        # trans_load invalidates ormcache but not record cache
        menu.env.cache.invalidate()
        self.assertEqual(menu.name, "New Name")
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom")

    def test_lang_with_base(self):
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_BE', module_name='test_translation_import', verbose=False)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr_BE.po', 'fr_BE', module_name='test_translation_import', verbose=False, context={'overwrite': True})

        # language override base language
        translations = self.env['ir.translation'].search([
            ('lang', '=', 'fr_BE'),
            ('value', '=like', '% belgian french'),
        ])
        self.assertEqual(len(translations), 2)

        # not specified localized language fallback on base language
        translations = self.env['ir.translation'].search([
            ('lang', '=', 'fr_BE'),
            ('src', '=', 'Efgh'),
            ('value', '=', 'Efgh in french'),
        ])
        self.assertEqual(len(translations), 1)
        translations = self.env['ir.translation'].search([
            ('lang', '=', 'fr_BE'),
            ('src', '=', 'Test translation with a code type but different line number in pot'),
            ('value', '=', 'Test traduction avec un type code mais différent numéro de ligne dans le pot'),
        ])
        self.assertEqual(len(translations), 1)

    def test_no_duplicate(self):
        """
        Just make sure we do not create duplicated translation with 'code' type
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
        ids = self.env['ir.translation'].search([
            ('lang', '=', 'fr_FR'),
            ('src', '=', 'Test translation with two code lines'),
        ])
        self.assertEqual(len(ids), 1)

        ids = self.env['ir.translation'].search([
            ('lang', '=', 'fr_FR'),
            ('src', '=', 'Test translation with a code type but different line number in pot'),
        ])
        self.assertEqual(len(ids), 1)

        ids = self.env['ir.translation'].search([
            ('lang', '=', 'fr_FR'),
            ('src', '=', 'Test translation with two code type and model'),
        ])
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(ids.filtered(lambda t: t.type == 'code')), 1)

    def test_export_empty_string(self):
        """When the string and the translation is equal the translation is empty"""
        # Export the translations
        def update_translations(context=None):
            context = dict(context or {}, overwrite=True)
            with closing(io.BytesIO()) as bufferobj:
                odoo.tools.trans_export('fr_FR', ['test_translation_import'], bufferobj, 'po', self.cr)
                bufferobj.name = 'test_translation_import/i18n/fr.po'
                odoo.tools.trans_load_data(self.cr, bufferobj, 'po', 'fr_FR', verbose=False, context=context)

        # Check that the not translated key is not created
        update_translations()
        translation = self.env['ir.translation'].search_count([('src', '=', 'Efgh'), ('value', '=', '')])
        self.assertFalse(translation, 'An empty translation is not imported')

        # Check that "Generate Missing Terms" create empty string for not translated key
        update_translations({'create_empty_translation': True})
        translation = self.env['ir.translation'].search_count([('src', '=', 'Efgh'), ('value', '=', '')])
        self.assertTrue(translation, 'The translation of "Efgh" should be empty')

        # Modify the value translated for the equal value of the key
        menu = self.env.ref('test_translation_import.menu_test_translation_import')
        menu.name = "New Name"
        menu.with_context(lang='fr_FR').name = "New Name"
        update_translations()
        self.assertEqual(menu.with_context(lang='fr_FR').name, "New Name", 'The translation of "New Name" should be "New Name"')

        # Modify the value translated for another different value
        menu.name = "New Name"
        menu.with_context(lang='fr_FR').name = "Nouveau nom"
        update_translations()
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom", 'The translation of "New Name" should be "Nouveau nom"')

    def test_import_from_po_file(self):
        """Test the import from a single po file works"""
        with file_open('test_translation_import/i18n/tlh.po', 'rb') as f:
            po_file = base64.encodestring(f.read())

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

        trans_count = self.env['ir.translation'].search_count([('lang', '=', 'tlh')])
        self.assertEqual(trans_count, 1, "The imported translations were not created")

        self.env.context = dict(self.env.context, lang="tlh")
        self.assertEqual(_("Klingon"), "tlhIngan", "The code translation was not applied")

    def test_lazy_translation(self):
        """Test the import from a single po file works"""
        with file_open('test_translation_import/i18n/tlh.po', 'rb') as f:
            po_file = base64.encodestring(f.read())

        import_tlh = self.env["base.language.import"].create({
            'name': 'Klingon',
            'code': 'tlh',
            'data': po_file,
            'filename': 'tlh.po',
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_tlh.import_lang()

        context = {'lang': "tlh"}
        self.assertEqual(_("Klingon"), "tlhIngan", "The direct code translation was not applied")
        context = None

        # Comparison of lazy strings must be explicitely casted to string
        with self.assertRaises(NotImplementedError):
            TRANSLATED_TERM == "Klingon"
        self.assertEqual(str(TRANSLATED_TERM), "Klingon", "The translation should not be applied yet")

        context = {'lang': "tlh"}
        self.assertEqual(str(TRANSLATED_TERM), "tlhIngan", "The lazy code translation was not applied")

    def test_import_from_csv_file(self):
        """Test the import from a single CSV file works"""
        with file_open('test_translation_import/i18n/dot.csv', 'rb') as f:
            po_file = base64.encodestring(f.read())

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

        trans_count = self.env['ir.translation'].search_count([('lang', '=', 'dot')])
        self.assertEqual(trans_count, 1, "The imported translations were not created")

        self.env.context = dict(self.env.context, lang="dot")
        self.assertEqual(_("Accounting"), "samva", "The code translation was not applied")

    def test_export_pollution(self):
        """ Test that exporting the translation only exports the translations of the module """
        with file_open('test_translation_import/i18n/dot.csv', 'rb') as f:
            csv_file = base64.b64encode(f.read())

        # dot.csv only contains one term
        import_tlh = self.env["base.language.import"].create({
            'name': 'Dothraki',
            'code': 'dot',
            'data': csv_file,
            'filename': 'dot.csv',
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_tlh.import_lang()

        # create a translation that has the same src as an existing field but no module
        # information and a different res_id that the real field
        # this translation should not be included in the export
        self.env['ir.translation'].create({
            'src': '1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB',
            'value': '1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB in Dothraki',
            'type': 'model',
            'name': 'ir.model.fields,field_description',
            'res_id': -1,
            'lang': 'dot',
        })
        module = self.env.ref('base.module_test_translation_import')
        export = self.env["base.language.export"].create({
            'lang': 'dot',
            'format': 'po',
            'modules': [(6, 0, [module.id])]
        })
        export.act_getfile()
        po_file = export.data
        reader = TranslationFileReader(base64.b64decode(po_file).decode(), fileformat='po')
        for row in reader:
            if row['value']:
                # should contains only one row from the csv, not the manual one
                self.assertEqual(row['src'], "Accounting")
                self.assertEqual(row['value'], "samva")


@tagged('post_install', '-at_install')
class TestTranslationFlow(common.TransactionCase):

    def test_export_import(self):
        """ Ensure export+import gives the same result as loading a language """
        # load language and generate missing terms to create missing empty terms
        with mute_logger('odoo.addons.base.models.ir_translation'):
            self.env["base.language.install"].create({'lang': 'fr_FR', 'overwrite': True}).lang_install()
        self.env["base.update.translations"].create({'lang': 'fr_FR'}).act_update()

        translations = self.env["ir.translation"].search([
            ('lang', '=', 'fr_FR'),
            ('module', '=', 'test_translation_import')
        ])

        # minus 3 as the original fr.po contains 3 fake code translations (cf
        # test_no_duplicate test) which are not found by babel_extract_terms
        init_translation_count = len(translations) - 3

        module = self.env.ref('base.module_test_translation_import')
        export = self.env["base.language.export"].create({
            'lang': 'fr_FR',
            'format': 'po',
            'modules': [(6, 0, [module.id])]
        })
        export.act_getfile()
        po_file = export.data
        self.assertIsNotNone(po_file)

        translations.unlink()

        import_fr = self.env["base.language.import"].create({
            'name': 'French',
            'code': 'fr_FR',
            'data': export.data,
            'filename': export.name,
            'overwrite': False,
        })
        with mute_logger('odoo.addons.base.models.res_lang'):
            import_fr.with_context(create_empty_translation=True).import_lang()

        import_translation = self.env["ir.translation"].search([
            ('lang', '=', 'fr_FR'),
            ('module', '=', 'test_translation_import')
        ])
        self.assertEqual(init_translation_count, len(import_translation))
