# -*- coding: utf-8 -*-
import unittest2
from openerp.tests import common

ANSWER_TO_ULTIMATE_QUESTION = 42

class TestAttributes(common.TransactionCase):
    def test_we_can_add_attributes(self):
        Model = self.registry('test_new_api.mock_model')
        instance = Model.create({})
        setattr(instance, 'useless_field', ANSWER_TO_ULTIMATE_QUESTION)

        # Does the attribute exist in the instance of the model ?
        self.assertTrue(hasattr(instance, 'useless_field'))

        # Is it the right type ?
        self.assertIsInstance(instance.useless_field, (int, long))

        # Is it the right value, in case of, we don't know ;-)
        self.assertEqual(instance.useless_field,
                         ANSWER_TO_ULTIMATE_QUESTION)

        # We are paranoiac !
        self.assertEqual(getattr(instance, 'useless_field'),
                         ANSWER_TO_ULTIMATE_QUESTION)