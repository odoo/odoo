# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.ir_config_parameter import _default_parameters
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
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

    def test_str_falsy_value(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertEqual(ICP.get_str('config_key'), '')
        self.assertEqual(ICP.get_str('config_key', 'undefined value'), 'undefined value')

        ICP.set_str('config_key', 'value')
        self.assertEqual(ICP.get_str('config_key', 'undefined value'), 'value')
        ICP.set_str('config_key', False)
        self.assertEqual(ICP.get_str('config_key', 'undefined value'), 'undefined value')

        ICP.set_str('config_key', 'value')
        self.assertEqual(ICP.get_str('config_key', 'undefined value'), 'value')
        # recommended way to explicitly set the  to undefined
        ICP.set_str('config_key', None)
        self.assertEqual(ICP.get_str('config_key', 'undefined value'), 'undefined value')

        ICP.set_str('config_key', 'value')
        config_record = ICP.search([('key', '=', 'config_key')], limit=1)
        self.assertEqual(config_record.value, 'value')
        config_record.value = False  # set the configuration to undefined
        self.assertIs(config_record.value, False)
        self.assertEqual(ICP.get_int('config_key', 'undefined value'), 'undefined value')

    def test_int_falsy_value(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertEqual(repr(ICP.get_int('config_key')), '0')
        self.assertEqual(ICP.get_int('config_key', 100), 100)

        ICP.set_int('config_key', 10)
        self.assertEqual(ICP.get_int('config_key', 100), 10)
        ICP.set_int('config_key', False)
        self.assertEqual(ICP.get_int('config_key', 100), 100)

        ICP.set_int('config_key', 10)
        self.assertEqual(ICP.get_int('config_key', 100), 10)
        # recommended way to explicitly set the configuration to undefined
        ICP.set_int('config_key', None)
        self.assertEqual(ICP.get_int('config_key', 100), 100)

        ICP.set_int('config_key', 0)
        self.assertEqual(ICP.get_int('config_key', 100), 0)

        config_record = ICP.search([('key', '=', 'config_key')], limit=1)
        self.assertEqual(config_record.value, '0')
        config_record.value = False  # set the configuration to undefined
        self.assertIs(config_record.value, False)
        self.assertEqual(ICP.get_int('config_key', 100), 100)

    def test_float_falsy_value(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertEqual(repr(ICP.get_float('config_key')), '0.0')
        self.assertEqual(ICP.get_float('config_key', 100.0), 100.0)

        ICP.set_float('config_key', 3.14)
        self.assertEqual(ICP.get_float('config_key', 100.0), 3.14)
        ICP.set_float('config_key', False)
        self.assertEqual(ICP.get_float('config_key', 100.0), 100.0)

        ICP.set_float('config_key', 3.14)
        self.assertEqual(ICP.get_float('config_key', 100.0), 3.14)
        # recommended way to explicitly set the configuration to undefined
        ICP.set_float('config_key', None)
        self.assertEqual(ICP.get_float('config_key', 100.0), 100.0)

        ICP.set_float('config_key', 0)
        self.assertEqual(repr(ICP.get_float('config_key', 100.0)), '0.0')

        config_record = ICP.search([('key', '=', 'config_key')], limit=1)
        self.assertEqual(config_record.value, '0.0')
        config_record.value = False  # set the configuration to undefined
        self.assertIs(config_record.value, False)
        self.assertEqual(ICP.get_float('config_key', 100.0), 100.0)

    def test_bool_falsy_value(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self.assertIs(ICP.get_bool('config_key'), False)
        self.assertEqual(ICP.get_bool('config_key', True), True)

        ICP.set_bool('config_key', True)
        self.assertEqual(ICP.get_bool('config_key', True), True)
        # set_bool(key, False) means explicitly setting the configuration to False
        ICP.set_bool('config_key', False)
        self.assertEqual(ICP.get_bool('config_key', True), False)

        ICP.set_bool('config_key', True)
        self.assertEqual(ICP.get_bool('config_key', True), True)
        ICP.set_bool('config_key', None)
        self.assertEqual(ICP.get_bool('config_key', True), True)

        ICP.set_bool('config_key', True)
        config_record = ICP.search([('key', '=', 'config_key')], limit=1)
        self.assertEqual(config_record.value, 'True')
        config_record.value = False  # set the configuration to undefined
        self.assertIs(config_record.value, False)
        self.assertEqual(ICP.get_int('config_key', True), True)

    def test_invalid_value_fixup(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.create({'key': 'config_key', 'value': 'invalid int value'})
        with self.assertLogs('odoo.addons.base.models.ir_config_parameter', level='WARNING') as logs:
            self.env.registry.clear_cache('stable')
            self.assertEqual(ICP.get_int('config_key', 100), 100)
            self.assertEqual(logs.output[0], "WARNING:odoo.addons.base.models.ir_config_parameter:ir.config_parameter with key config_key has invalid value 'invalid int value' for type int")

        with mute_logger('odoo.addons.base.models.ir_config_parameter'):
            ICP.set_int('config_key', None)

        with self.assertNoLogs('odoo.addons.base.models.ir_config_parameter', 'WARNING'):
            self.env.registry.clear_cache('stable')
            self.assertEqual(ICP.get_int('config_key', 100), 100)
