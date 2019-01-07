# -*- coding: utf-8 -*-

import odoo
from odoo.tests import common

class TestTermCount(common.TransactionCase):

    def test_count_term(self):
        """
        Just make sure we have as many translation entries as we wanted.
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
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
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
        menu.with_context(lang='fr_FR').name = "Nouveau nom"
        # reload with overwrite
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False, context={'overwrite': True})

        # trans_load invalidates ormcache but not record cache
        menu.refresh()
        self.assertEqual(menu.name, "New Name")
        self.assertEqual(menu.with_context(lang='fr_FR').name, "Nouveau nom")

    def test_no_duplicate(self):
        """
        Just make sure we do not create duplicated translation with 'code' type
        """
        odoo.tools.trans_load(self.cr, 'test_translation_import/i18n/fr.po', 'fr_FR', module_name='test_translation_import', verbose=False)
        ids = self.env['ir.translation'].search(
            [('src', '=', 'Test translation with two code lines')])
        self.assertEqual(len(ids), 1)

        ids = self.env['ir.translation'].search(
            [('src', '=', 'Test translation with a code type but different line number in pot')])
        self.assertEqual(len(ids), 1)

        ids = self.env['ir.translation'].search(
            [('src', '=', 'Test translation with two code type and model')])
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(ids.filtered(lambda t: t.type == 'code')), 1)
