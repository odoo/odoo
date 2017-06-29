# -*- coding: utf-8 -*-

import odoo
from odoo.tests import common

class TestTermCount(common.TransactionCase):

    def test_count_term(self):
        """
        Just make sure we have as many translation entries as we wanted.
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)
        ids = self.env['ir.translation'].search(
            [('src', '=', '1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB')])
        self.assertEqual(len(ids), 2)

    def test_noupdate(self):
        """
        Make sure no update do not overwrite translations
        """
        menu = self.env.ref('test_translation_import.menu_test_translation_import')
        menu.name = "New Name"
        # install french and change translation content
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False)
        menu.with_context(lang='fr_FR').name = "Nouveau nom"
        # reload with overwrite
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', verbose=False, context={'overwrite': True})

        # trans_load invalidates ormcache but not record cache
        menu.refresh()
        self.assertEqual(menu.name, "New Name")
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom")

    def test_export_empty_string(self):
        """
        When the string and the translation is equal the translation is empty
        """
        # Export the translations
        with odoo.tools.misc.file_open('test_translation_import/i18n/es.po', 'w+b') as bufferobj:
            odoo.tools.trans_export('es_ES', ['test_translation_import'], bufferobj, 'po', self.cr)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/es.po', 'es_ES', verbose=False)
        languages = self.env['ir.translation'].search([])
        # Check if the not translated key is empty string
        empty_value = [item for item in languages if item.src == 'Efgh']
        self.assertEqual(len(empty_value), 1)
        self.assertEqual(empty_value[0].value, '')
        # Modify the value translated for the equal value of the key
        menu = self.env.ref('test_translation_import.menu_test_translation_import')
        menu.name = "New Name"
        menu.with_context(lang='es_ES').name = "New Name"
        with odoo.tools.misc.file_open('test_translation_import/i18n/es.po', 'w+b') as bufferobj:
            odoo.tools.trans_export('es_ES', ['test_translation_import'], bufferobj, 'po', self.cr)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/es.po', 'es_ES', verbose=False, context={'overwrite': True})
        menu.refresh()
        self.assertEqual(menu.with_context(lang='es_ES').name, "New Name")
        # Modify the value translated for another diferent value
        menu.name = "New Name"
        menu.with_context(lang='es_ES').name = "Nuevo Nombre"
        with odoo.tools.misc.file_open('test_translation_import/i18n/es.po', 'w+b') as bufferobj:
            odoo.tools.trans_export('es_ES', ['test_translation_import'], bufferobj, 'po', self.cr)
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/es.po', 'es_ES', verbose=False, context={'overwrite': True})
        menu.refresh()
        self.assertEqual(menu.with_context(lang='es_ES').name, "Nuevo Nombre")

