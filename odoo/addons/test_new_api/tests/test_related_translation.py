# -*- coding: utf-8 -*-
import io

import odoo.tests
from odoo.tools.translate import TranslationImporter


@odoo.tests.tagged('post_install', '-at_install')
class TestRelatedTranslation(odoo.tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.test1 = cls.env['test_new_api.related_translation_1'].with_context(lang='en_US').create({
            'name': 'Knife',
            'html': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
        })
        cls.test1.with_context(lang='fr_FR').write({
            'name': 'Couteau',
        })
        cls.test1.update_field_translations('html', {'fr_FR': {
            'Knife': 'Couteau',
            'Fork': 'Fourchette',
            'Spoon': 'Cuiller',
        }})
        cls.test12 = cls.env['test_new_api.related_translation_1'].with_context(lang='en_US').create({
            'name': 'Knife 2',
            'html': '<p>Knife 2</p><p>Fork 2</p><p>Spoon 2</p>',
        })
        cls.test12.with_context(lang='fr_FR').write({
            'name': 'Couteau 2',
        })
        cls.test12.update_field_translations('html', {'fr_FR': {
            'Knife 2': 'Couteau 2',
            'Fork 2': 'Fourchette 2',
            'Spoon 2': 'Cuiller 2',
        }})
        cls.test2 = cls.env['test_new_api.related_translation_2'].with_context(lang='en_US').create({
            'related_id': cls.test1.id,
        })
        cls.test3 = cls.env['test_new_api.related_translation_3'].with_context(lang='en_US').create({
            'related_id': cls.test2.id,
        })

    def test_read(self):
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'Knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'Knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'Knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Couteau')

    def test_write_from_ori(self):
        self.test1.with_context(lang='en_US').name = 'New knife'
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Couteau')
        self.test1.with_context(lang='fr_FR').name = 'Nouveau couteau'
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Nouveau couteau')

    def test_write_from_related(self):
        self.test2.with_context(lang='en_US').name = 'New knife'
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Couteau')
        self.test3.with_context(lang='fr_FR').name = 'Nouveau couteau'
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Nouveau couteau')

    def test_translate_from_ori(self):
        self.test1.update_field_translations('name', {'en_US': 'New knife'})
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_name, 'Couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Couteau')
        self.test1.update_field_translations('name', {'fr_FR': 'Nouveau couteau'})
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_name, 'Nouveau couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Nouveau couteau')

    def test_translate_from_related(self):
        self.test2.update_field_translations('name', {'en_US': 'New knife'})
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_name, 'Couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Couteau')
        self.test3.update_field_translations('name', {'fr_FR': 'Nouveau couteau'})
        self.assertEqual(self.test1.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test1.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Nouveau couteau')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_name, 'New knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_name, 'Nouveau couteau')
        self.assertEqual(self.test3.with_context(lang='en_US').name, 'New knife')
        self.assertEqual(self.test3.with_context(lang='fr_FR').name, 'Nouveau couteau')

    def test_import_from_po(self):
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        test1_xml_id = self.test1.export_data(['id']).get('datas')[0][0]
        po_string = '''
                #. module: test_new_api
                #: model:test_new_api.related_translation_1,name:%s
                msgid "Knife"
                msgstr "Nouveau couteau"
                ''' % test1_xml_id
        with io.BytesIO(bytes(po_string, encoding='utf-8')) as f:
            f.name = 'dummy'
            translation_importer = TranslationImporter(self.env.cr, verbose=True)
            translation_importer.load(f, 'po', 'fr_FR')
            translation_importer.save(overwrite=True)
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Nouveau couteau')

    def test_write_from_ori_term(self):
        self.test1.with_context(lang='fr_FR').html = '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_delay_write_from_ori_term(self):
        self.test1.with_context(lang='fr_FR', delay_translations=True).html = '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

        self.assertEqual(self.test1.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_translate_from_ori_term(self):
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.test1.update_field_translations('html', {'fr_FR': {'Knife': 'Nouveau couteau'}})
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_write_from_related_term(self):
        self.test3.with_context(lang='fr_FR').html = '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_write_from_related_term_more(self):
        # same as above, but making sure that the related field's cache is invalidated
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.test2.with_context(lang='fr_FR').html = '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_delay_write_from_related_term(self):
        self.test3.with_context(lang='fr_FR', delay_translations=True).html = '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

        self.assertEqual(self.test1.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US', check_translations=True).html, '<p>Nouveau couteau</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR', check_translations=True).html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_translate_from_related_term(self):
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.test3.update_field_translations('html', {'fr_FR': {'Knife': 'Nouveau couteau'}})
        self.assertEqual(self.test1.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test1.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test2.with_context(lang='en_US').computed_html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test2.with_context(lang='fr_FR').computed_html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>')

    def test_translate_change_many2one(self):
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'Knife')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau')
        self.test2.with_context(lang='fr_FR').related_id = self.test12
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'Knife 2')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau 2')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife 2</p><p>Fork 2</p><p>Spoon 2</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Couteau 2</p><p>Fourchette 2</p><p>Cuiller 2</p>')
        self.test2.invalidate_recordset()
        self.assertEqual(self.test2.with_context(lang='en_US').name, 'Knife 2')
        self.assertEqual(self.test2.with_context(lang='fr_FR').name, 'Couteau 2')
        self.assertEqual(self.test3.with_context(lang='en_US').html, '<p>Knife 2</p><p>Fork 2</p><p>Spoon 2</p>')
        self.assertEqual(self.test3.with_context(lang='fr_FR').html, '<p>Couteau 2</p><p>Fourchette 2</p><p>Cuiller 2</p>')

    def test_translate_mapped(self):
        self.assertEqual(self.test2.with_context(lang='en_US').mapped('name'), ['Knife'])
        self.test1.with_context(lang='en_US').name = 'New knife'
        self.assertEqual(self.test1.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test1.with_context(lang='fr_FR').mapped('name'), ['Couteau'])
        self.assertEqual(self.test2.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test2.with_context(lang='en_US').mapped('related_id.name'), ['New knife'])
        self.assertEqual(self.test2.with_context(lang='fr_FR').mapped('name'), ['Couteau'])
        self.assertEqual(self.test2.with_context(lang='fr_FR').mapped('related_id.name'), ['Couteau'])
        self.assertEqual(self.test3.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test3.with_context(lang='fr_FR').mapped('related_id.name'), ['Couteau'])
        self.assertEqual(self.test3.with_context(lang='fr_FR').mapped('name'), ['Couteau'])
        self.assertEqual(self.test3.with_context(lang='fr_FR').mapped('related_id.name'), ['Couteau'])
        self.test1.with_context(lang='fr_FR').name = 'Nouveau couteau'
        self.assertEqual(self.test1.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test1.with_context(lang='fr_FR').mapped('name'), ['Nouveau couteau'])
        self.assertEqual(self.test2.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test2.with_context(lang='en_US').mapped('related_id.name'), ['New knife'])
        self.assertEqual(self.test2.with_context(lang='fr_FR').mapped('name'), ['Nouveau couteau'])
        self.assertEqual(self.test2.with_context(lang='fr_FR').mapped('related_id.name'), ['Nouveau couteau'])
        self.assertEqual(self.test3.with_context(lang='en_US').mapped('name'), ['New knife'])
        self.assertEqual(self.test3.with_context(lang='en_US').mapped('related_id.name'), ['New knife'])
        self.assertEqual(self.test3.with_context(lang='fr_FR').mapped('name'), ['Nouveau couteau'])
        self.assertEqual(self.test3.with_context(lang='fr_FR').mapped('related_id.name'), ['Nouveau couteau'])

    def test_new_records(self):
        self.env['res.lang']._activate_lang('nl_NL')
        model = self.env['test_new_api.related_translation_1']

        # The value in env lang should persist after reading the second lang value
        record_en = model.new({'name': 'en'})
        record_fr = record_en.with_context(lang='fr_FR')
        record_nl = record_fr.with_context(lang='nl_NL')
        self.assertEqual(record_fr.name, 'en')
        self.assertEqual(record_en.name, 'en')

        record_fr.name = 'fr'
        self.assertEqual(record_en.name, 'en')
        self.assertEqual(record_fr.name, 'fr')
        self.assertEqual(record_nl.name, 'en')

        # The value in second lang should persist after reading the env lang value
        record_fr = model.with_context(lang='fr_FR').new({'name': 'fr'})
        record_en = record_fr.with_context(lang=None)
        record_nl = record_fr.with_context(lang='nl_NL')
        self.assertEqual(record_en.name, 'fr')
        self.assertEqual(record_nl.name, 'fr')
        self.assertEqual(record_fr.name, 'fr')

        # get() on a third language should fallback to the value in en_US that was set by default
        record_fr = model.with_context(lang='fr_FR').new({'name': 'fr'})
        record_en = record_fr.with_context(lang=None)
        record_nl = record_fr.with_context(lang='nl_NL')
        self.assertEqual(record_nl.name, 'fr')
        self.assertEqual(record_fr.name, 'fr')
        self.assertEqual(record_en.name, 'fr')

        # _update_cache should not nullify the values in other langs
        record_en = model.new({'name': 'en'})
        record_fr = record_en.with_context(lang='fr_FR')
        record_fr._update_cache({'name': 'fr'}, validate=False)
        self.assertEqual(record_en.name, 'en')
        self.assertEqual(record_fr.name, 'fr')

        # update should not nullify the values in other langs
        record_en = model.new({'name': 'en'})
        record_fr = record_en.with_context(lang='fr_FR')
        record_fr.name = 'fr'
        self.assertEqual(record_en.name, 'en')
        self.assertEqual(record_fr.name, 'fr')

        # check with computed field
        child_en = self.env['test_new_api.related_translation_2'].new({'related_id': record_en.id})
        child_fr = child_en.with_context(lang='fr_FR')
        self.assertEqual(child_fr.name, 'fr')
        self.assertEqual(child_en.name, 'en')
        self.assertEqual(child_fr.computed_name, 'fr')
        self.assertEqual(child_en.computed_name, 'en')

    def test_new_records_html(self):
        model = self.env['test_new_api.related_translation_1']

        record_en = model.create({'html': '<p>Knife</p><p>Fork</p><p>Spoon</p>'})
        record_fr = record_en.with_context(lang='fr_FR')
        record_fr.html = '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>'
        # expected behavior since the user `write` instead of `update_field_translations`
        self.assertEqual(record_en.html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
        self.assertEqual(record_fr.html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')

        record_en = model.new({'html': '<p>Knife</p><p>Fork</p><p>Spoon</p>'})
        record_fr = record_en.with_context(lang='fr_FR')
        record_fr.html = '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>'
        # inconsistent behavior but usually users don't care or may even be happy about it
        self.assertEqual(record_en.html, '<p>Knife</p><p>Fork</p><p>Spoon</p>')
        self.assertEqual(record_fr.html, '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>')
