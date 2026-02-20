import io

import odoo.tests
from odoo.tools.translate import TranslationImporter
from odoo.exceptions import ValidationError


@odoo.tests.tagged('post_install', '-at_install')
class TestRelatedTranslation(odoo.tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.test1 = cls.env['test_orm.related_translation_1'].with_context(lang='en_US').create({
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
        cls.test12 = cls.env['test_orm.related_translation_1'].with_context(lang='en_US').create({
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
        cls.test2 = cls.env['test_orm.related_translation_2'].with_context(lang='en_US').create({
            'related_id': cls.test1.id,
        })
        cls.test3 = cls.env['test_orm.related_translation_3'].with_context(lang='en_US').create({
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
                #. module: test_orm
                #: model:test_orm.related_translation_1,name:%s
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
        model = self.env['test_orm.related_translation_1']

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
        child_en = self.env['test_orm.related_translation_2'].new({'related_id': record_en.id})
        child_fr = child_en.with_context(lang='fr_FR')
        self.assertEqual(child_fr.name, 'fr')
        self.assertEqual(child_en.name, 'en')
        self.assertEqual(child_fr.computed_name, 'fr')
        self.assertEqual(child_en.computed_name, 'en')

    def test_new_records_html(self):
        model = self.env['test_orm.related_translation_1']

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

    def _check_translation_value(self, record, expected):
        for _ in range(2):
            # first time check cache value
            # second time check refetched/recomputed value
            for field_name, expected_dict in expected.items():
                if not expected_dict:
                    self.assertEqual(record[field_name], False)
                else:
                    for lang, value in expected_dict.items():
                        self.assertEqual(record.with_context(lang=lang)[field_name], value)
            record.invalidate_recordset()

    def test_create_translated_dict(self):
        self.env['res.lang']._activate_lang('nl_NL')
        model = self.env['test_orm.related_translation_1'].with_context(lang='en_US')
        record = model.create({
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau'
            },
            'html': {
                'en_US': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>'
            }
        })

        self._check_translation_value(record, {
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau',
                'nl_NL': 'Knife',
            },
            'html': {
                'en_US': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>',
                'nl_NL': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
            }
        })
    
    def test_create_related_translated_dict(self):
        self.env['res.lang']._activate_lang('nl_NL')
        model = self.env['test_orm.related_translation_4'].with_context(lang='en_US')
        record = model.create({
            'related_id': self.test1.id,
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau'
            },
            'html': {
                'en_US': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>'
            }
        })

        self._check_translation_value(record, {
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau',
                'nl_NL': 'Knife',
            },
            'html': {
                'en_US': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau</p><p>Fourchette</p><p>Cuiller</p>',
                'nl_NL': '<p>Knife</p><p>Fork</p><p>Spoon</p>',
            }
        })

    def test_write_translated_dict(self):
        self.env['res.lang']._activate_lang('nl_NL')

        test1_en = self.test1.with_context(lang='en_US')
        test1_fr = self.test1.with_context(lang='fr_FR')
        test1_nl = test1_fr.with_context(lang='nl_NL')
        test1_en.name = {'fr_FR': 'Couteau 2'}
        test1_en.html = {'fr_FR': '<p>Couteau 2</p><p>Fourchette</p><p>Cuiller</p>'}
        self._check_translation_value(test1_en, {
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau 2',
                'nl_NL': 'Knife',
            },
            'html': {
                'en_US': '<p>Couteau 2</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau 2</p><p>Fourchette</p><p>Cuiller</p>',
                'nl_NL': '<p>Couteau 2</p><p>Fork</p><p>Spoon</p>',
            }
        })

        test1_en.name = {'fr_FR': 'Couteau 3', 'nl_NL': 'Mes 3'}
        test1_en.html = {'fr_FR': '<p>Couteau 3</p><p>Fourchette</p><p>Cuiller</p>', 'nl_NL': '<p>Mes 3</p><p>Vork 3</p><p>Lepel 3</p>'}
        self._check_translation_value(test1_en, {
            'name': {
                'en_US': 'Knife',
                'fr_FR': 'Couteau 3',
                'nl_NL': 'Mes 3',
            },
            'html': {
                # since en_US (test1_env.env.lang) not in the dict, fr_FR as the first key will be the write language
                'en_US': '<p>Couteau 3</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau 3</p><p>Fourchette</p><p>Cuiller</p>',
                'nl_NL': '<p>Mes 3</p><p>Vork 3</p><p>Lepel 3</p>',
            }
        })

        test1_en.name = {'en_US': 'Knife4', 'fr_FR': 'Nouveau couteau4'}
        test1_en.html = {'fr_FR': '<p>Couteau 4</p><p>Fourchette</p><p>Cuiller</p>', 'en_US': '<p>Knife 4</p><p>Fork</p><p>Spoon</p>'}
        self._check_translation_value(test1_en, {
            'name': {
                'en_US': 'Knife4',
                'fr_FR': 'Nouveau couteau4',
                'nl_NL': 'Mes 3',
            },
            'html': {
                # since en_US (test1_env.env.lang) is in the dict, it will be the write language
                'en_US': '<p>Knife 4</p><p>Fork</p><p>Spoon</p>',
                'fr_FR': '<p>Couteau 4</p><p>Fourchette</p><p>Cuiller</p>',
                'nl_NL': '<p>Knife 4</p><p>Vork 3</p><p>Lepel 3</p>',
            }
        })
        self.assertEqual(test1_en.name, 'Knife4')
        self.assertEqual(test1_fr.name, 'Nouveau couteau4')
        self.assertEqual(test1_nl.name, 'Mes 3')

        with self.assertRaises(ValidationError):
            # <p> is not consistent with <a>
            test1_en.html = {'en_US': '<p>Knife 5</p><p>Fork</p><p>Spoon</p>', 'fr_FR': '<a>Couteau 5</a><p>Fourchette</p><p>Cuiller</p>'}

        with self.assertRaises(ValidationError):
            # inconsistent term numbers (2 vs 3)
            test1_en.html = {'en_US': '<p>Knife 6</p><p>Fork</p><p>Spoon</p>', 'fr_FR': '<p></p><p>Fourchette</p><p>Cuiller</p>'}

    def test_write_translated_dict_relation(self):
        self.env['res.lang']._activate_lang('nl_NL')
        test1_en = self.test1.with_context(lang='en_US')
        test1_en.name = {'en_US': 'New knife', 'fr_FR': 'Nouveau couteau'}
        test1_en.html = {'en_US': '<p>New knife</p><p>Fork</p><p>Spoon</p>', 'fr_FR': '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>'}

        expected_name_dict = {
            'en_US': 'New knife',
            'fr_FR': 'Nouveau couteau',
            'nl_NL': 'New knife',
        }
        expected_html_dict = {
            'en_US': '<p>New knife</p><p>Fork</p><p>Spoon</p>',
            'fr_FR': '<p>Nouveau couteau</p><p>Fourchette</p><p>Cuiller</p>',
            'nl_NL': '<p>New knife</p><p>Fork</p><p>Spoon</p>',
        }
    
        self._check_translation_value(test1_en, {
            'name': expected_name_dict,
            'html': expected_html_dict,
        })

        test2_en = self.test2.with_context(lang='en_US')
        # non-store related fields
        self._check_translation_value(test2_en, {
            'name': expected_name_dict,
            'html': expected_html_dict,
        })
        # non stored context dependent computed fields
        self._check_translation_value(test2_en, {
            'computed_name': expected_name_dict,
            'computed_html': expected_html_dict,
        })
        # stored computed translated fields
        self._check_translation_value(test2_en, {
            'computed_translated_name': expected_name_dict,
            'computed_translated_html': expected_html_dict,
        })

    def test_constraints(self):
        # Expected behavior: The check for non current language won't be triggered
        self.test1.with_context(lang='en_US').name = {'en_US': 'New knife', 'fr_FR': 'x'}
        with self.assertRaises(ValidationError):
            self.test1.with_context(lang='en_US').name = {'en_US': 'x', 'fr_FR': 'Nouveau couteau'}

        with self.assertRaises(ValidationError):
            self.test1.with_context(lang='en_US').html = {'en_US': '<a>Knife</a>', 'fr_FR': '<a>x</a>'}
