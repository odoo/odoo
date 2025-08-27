# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.ir_config_parameter import _default_parameters
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIrConfigParameter(TransactionCase):

    def test_default_parameters(self):
        """ Check the behavior of _default_parameters
        when updating keys and deleting records. """
        for key in _default_parameters:
            config_parameter = self.env['ir.config_parameter'].search([('key', '=', key)], limit=1)
            with self.assertRaises(ValidationError):
                config_parameter.unlink()

            new_key = f"{key}_updated"
            with self.assertRaises(ValidationError):
                config_parameter.write({'key': new_key})

    def test_get_set_param(self):
        key = 'base._test_ir_config_parameter'
        ICP = self.env['ir.config_parameter']

        self.assertEqual(ICP.get_param(key), False)

        test_values = [
            (True, 'True'),
            (False, False),
            (1, '1'),
            (0, '0'),
            ('True', 'True'),
            ('False', 'False'),
            (1.0, '1.0'),
            (1 / 3, str(1 / 3)),
            (0.0, '0.0'),
            ({}, '{}'),
            ({'key': 'value'}, str({'key': 'value'})),
            ([], '[]'),
            ([1, 2, 3], '[1, 2, 3]'),
            ("value", 'value'),
            (None, False),
            ('', False),
        ]

        for set_value, get_value in test_values:
            ICP.set_param(key, set_value)
            self.assertEqual(ICP.get_param(key), get_value)

    def test_get_set(self):
        key = 'base._test_ir_config_parameter'
        ICP = self.env['ir.config_parameter']

        self.assertEqual(ICP.get(key), None)
        self.assertEqual(ICP.get_param(key), False)

        # value_type, set_value, get_value, get_param_value
        test_values = [
            ('bool', True, True, 'True'),
            ('bool', False, False, False),
            ('bool', '', False, False),
            ('int', 1, 1, '1'),
            ('int', 0, 0, False),
            ('int', False, False, False),
            ('int', '', 0, False),
            ('int', 3.6, 3, '3'),
            ('str', 'True', 'True', 'True'),
            ('str', 'False', 'False', 'False'),
            ('float', 1.0, 1.0, '1.0'),
            ('float', 1 / 3, 1 / 3, str(1 / 3)),  # todo imp float cmp
            ('float', 0.0, 0.0, False),
            ('float', False, False, False),
            ('str', {}, '{}', '{}'),
            ('str', {'key': 'value'}, str({'key': 'value'}), str({'key': 'value'})),
            ('str', [], '[]', '[]'),
            ('str', [1, 2, 3], '[1, 2, 3]', '[1, 2, 3]'),
            ('str', 'value', 'value', 'value'),
            ('str', None, '', False),
            ('str', False, '', False),
            ('str', '', '', False)
        ]

        for num, (value_type, set_value, get_value, get_param_value) in enumerate(test_values):
            key_ = f'{key}_{num}'
            ICP.set(key_, set_value, value_type)
            if value_type == 'bool':
                self.assertIs(ICP.get(key_), get_value)
                self.assertEqual(ICP.get_param(key_), get_param_value)
            elif value_type == 'int':
                value = ICP.get(key_)
                self.assertEqual(type(value).__name__, 'int')
                self.assertEqual(ICP.get_param(key_), get_param_value)
                self.assertEqual(value, get_value)
            elif value_type == 'float':
                value = ICP.get(key_)
                self.assertEqual(type(value).__name__, 'float')
                self.assertEqual(value, get_value)
                self.assertEqual(ICP.get_param(key_), get_param_value)
            elif value_type == 'str':
                value = ICP.get(key_)
                self.assertEqual(type(value).__name__, 'str')
                self.assertEqual(value, get_value)
                self.assertEqual(ICP.get_param(key_), get_param_value)
            else:
                raise ValueError(f"Invalid value_type: {value_type}")
