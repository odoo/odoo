# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.tagged('post_install', '-at_install')
class TestTranslationUnique(odoo.tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['test.translation.unique.model1'].create_unique_index_for_translated_field('name')
        cls.test1 = cls.env['test.translation.unique.model1'].with_context(lang='en_US').create({
            'name': 'Knife',
        })
        cls.test1.with_context(lang='fr_FR').write({
            'name': 'Couteau',
        })
        cls.test2 = cls.env['test.translation.unique.model1'].with_context(lang='en_US').create({
            'name': 'Knife_copy_[2]',
        })
        cls.test2.with_context(lang='fr_FR').write({
            'name': 'Couteau_copy_[2]',
        })
        cls.test3 = cls.env['test.translation.unique.model1'].with_context(lang='en_US').create({
            'name': 'Fork',
        })
        cls.test3.with_context(lang='fr_FR').write({
            'name': 'Fourchette',
        })


    def test_get_unique_field_value(self):
        unique_field_value = self.test3.get_unique_field_value('Knife')
        self.assertEqual(unique_field_value(self.test1), 'Knife')
        self.assertEqual(unique_field_value(self.test2), 'Knife_copy_[2]')
        self.assertEqual(unique_field_value(self.test3), 'Knife_copy_[3]')
        self.assertEqual(unique_field_value(self.test3), 'Knife_copy_[4]')
        self.assertEqual(unique_field_value(), 'Knife_copy_[5]')

    def test_get_unique_field_index(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['test.translation.unique.model1'].with_context(lang='fr_FR').create({
                'name': 'Couteau',
            })
