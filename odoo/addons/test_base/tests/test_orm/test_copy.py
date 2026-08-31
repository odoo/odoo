import odoo.tests
from odoo.tools.translate import StoredTranslations, mark_as_copy, code_translations


class TestCopyTranslations(odoo.tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        # mark_as_copy uses env._ from odoo.tools.translate → module "base"
        key = ('base', 'fr_FR')
        previous = code_translations.get_python_translations(*key)
        code_translations.python_translations[key] = {
            **previous,
            '%s (copy)': '%s (copie)',
        }
        cls.addClassCleanup(code_translations.python_translations.__setitem__, key, previous)

        cls.record = cls.env['test_orm.message'].with_context(lang='en_US').create({
            'label': 'Knife',
        })
        cls.record.with_context(lang='fr_FR').label = 'Couteau'
        cls.record_no_data = cls.env['test_orm.message'].create({})

    def test_copy_without_default(self):
        vals = self.record.copy_data()[0]
        self.assertIsInstance(vals['label'], StoredTranslations)
        self.assertEqual(dict(vals['label']), {
            'en_US': 'Knife',
            'fr_FR': 'Couteau',
        })
        copy = self.record.copy()
        self.assertEqual(copy.with_context(lang='en_US').label, 'Knife')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Couteau')

        vals = self.record_no_data.copy_data()[0]
        self.assertFalse(vals['label'])
        copy = self.record_no_data.copy()
        self.assertFalse(copy.label)

    def test_copy_with_default(self):
        vals = self.record.copy_data({'label': 'Custom Name'})[0]
        self.assertEqual(vals['label'], 'Custom Name')
        copy = self.record.copy({'label': 'Custom Name'})
        self.assertEqual(copy.with_context(lang='en_US').label, 'Custom Name')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Custom Name')

        vals = self.record.copy_data({'label': {'en_US': 'Fork', 'fr_FR': 'Fourchette'}})[0]
        self.assertEqual(vals['label'], {'en_US': 'Fork', 'fr_FR': 'Fourchette'})
        copy = self.record.copy({'label': {'en_US': 'Fork', 'fr_FR': 'Fourchette'}})
        self.assertEqual(copy.with_context(lang='en_US').label, 'Fork')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Fourchette')

    def test_mark_as_copy_without_default(self):
        self.patch(self.record._fields['label'], 'copy', mark_as_copy('label'))
        vals = self.record.copy_data()[0]
        self.assertIsInstance(vals['label'], StoredTranslations)
        self.assertEqual(dict(vals['label']), {
            'en_US': 'Knife (copy)',
            'fr_FR': 'Couteau (copie)',
        })
        copy = self.record.copy()
        self.assertEqual(copy.with_context(lang='en_US').label, 'Knife (copy)')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Couteau (copie)')

        vals = self.record_no_data.copy_data()[0]
        self.assertFalse(vals['label'])
        copy = self.record_no_data.copy()
        self.assertFalse(copy.label)

    def test_mark_as_copy_with_default(self):
        self.patch(self.record._fields['label'], 'copy', mark_as_copy('label'))
        vals = self.record.copy_data({'label': 'Custom Name'})[0]
        self.assertEqual(vals['label'], 'Custom Name')
        copy = self.record.copy({'label': 'Custom Name'})
        self.assertEqual(copy.with_context(lang='en_US').label, 'Custom Name')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Custom Name')

        vals = self.record.copy_data({'label': {'en_US': 'Fork', 'fr_FR': 'Fourchette'}})[0]
        self.assertEqual(vals['label'], {'en_US': 'Fork', 'fr_FR': 'Fourchette'})
        copy = self.record.copy({'label': {'en_US': 'Fork', 'fr_FR': 'Fourchette'}})
        self.assertEqual(copy.with_context(lang='en_US').label, 'Fork')
        self.assertEqual(copy.with_context(lang='fr_FR').label, 'Fourchette')
