# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.tools import pycompat

ANSWER_TO_ULTIMATE_QUESTION = 42

class TestAttributes(common.TransactionCase):

    def test_we_can_add_attributes(self):
        Model = self.env['test_new_api.category']
        instance = Model.create({'name': 'Foo'})

        # assign an unknown attribute
        instance.unknown = ANSWER_TO_ULTIMATE_QUESTION

        # Does the attribute exist in the instance of the model ?
        self.assertTrue(hasattr(instance, 'unknown'))

        # Is it the right type ?
        self.assertIsInstance(instance.unknown, pycompat.integer_types)

        # Is it the right value, in case of, we don't know ;-)
        self.assertEqual(instance.unknown, ANSWER_TO_ULTIMATE_QUESTION)

        # We are paranoiac !
        self.assertEqual(getattr(instance, 'unknown'), ANSWER_TO_ULTIMATE_QUESTION)
