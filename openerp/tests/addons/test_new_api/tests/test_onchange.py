# -*- coding: utf-8 -*-
import unittest2
from openerp.tests import common

class TestOnChange(common.TransactionCase):
    def setUp(self):
        super(TestOnChange, self).setUp()
        self.Model = self.registry('test_new_api.on_change')

    @unittest2.expectedFailure
    def test_default_get(self):
        # default_get behavior makes no sense? store=False fields are
        # completely ignored, but Field.null() does not matter a bit so this
        # yields a default for description but not trick or name_size
        fields = self.Model.fields_get()
        values = self.Model.default_get(fields.keys())
        self.assertEqual(values, {})

    @unittest2.expectedFailure
    def test_get_field(self):
        # BaseModel.__getattr__ always falls back to _get_field without caring
        # whether what is requested is or is not a field. And _get_field expects
        # to be called on a record and a record only, not on a model
        with self.assertRaises(AttributeError):
            self.Model.not_really_a_method()

    def test_new_onchange_unsaved(self):
        changed = self.Model.onchange('name', {
            'name': u"Bob the Builder",
            'name_size': 0,
            'name_utf8_size': 0,
            'description': False,
        })
        self.assertEqual(changed, {
            'name_size': 15,
            'name_utf8_size': 15,
            'description': u"Bob the Builder (15:15)"
        })

        changed = self.Model.onchange('description', {
            'name': u"Bob the Builder",
            'name_size': 15,
            'name_utf8_size': 15,
            'description': u"Can we fix it? Yes we can!"
        })
        self.assertEqual(changed, {})
