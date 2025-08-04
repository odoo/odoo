from datetime import datetime

from odoo.tests.common import TransactionCase
from odoo.fields import Datetime
from freezegun import freeze_time

# the res_config_write_value for res_config_setting_values to simulate a never customized setting
DEFAULT_SETTING = object()

class TestConfigSettings(TransactionCase):
    """Test res.config.settings functionality
    
    res.config.settings
    """

    def _test_field(self, field_name, res_config_setting_values, get_param_values):
        ResConfigSettings = self.env['res.config.settings']
        IrConfigParameter = self.env['ir.config_parameter']
        config_parameter = ResConfigSettings._fields[field_name].config_parameter

        res_config_write_value, res_config_get_value = res_config_setting_values

        # res.config.settings: set_values
        if res_config_write_value is DEFAULT_SETTING:
            self.env['ir.config_parameter'].search([('key', '=', config_parameter)]).unlink()
        else:
            self.config_settings = ResConfigSettings.create({})
            self.config_settings[field_name] = res_config_write_value
            self.config_settings.set_values()

        # res.config.settings: get_values
        new_config = ResConfigSettings.create({})
        if res_config_get_value is False:
            self.assertIs(new_config[field_name], False)
        else:
            self.assertEqual(new_config[field_name], res_config_get_value)

        # ir.config_parameter: get_param
        for get_param_default, get_param_value in get_param_values:
            if get_param_value is False:
                self.assertIs(IrConfigParameter.get_param(config_parameter, get_param_default), False)
            else:
                self.assertEqual(IrConfigParameter.get_param(config_parameter, get_param_default), get_param_value)

    def test_boolean_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [('False', 'False'), (False, False)]),
            ([False, False], [('False', 'False'), (False, False)]),
            ([True, True], [('False', 'True'), (False, 'True')]),
        ]

        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_boolean_field', res_config_setting_values, get_param_values)

        # technically possible, but developer will easily notice the behavior doesn't suit for the business
        field = self.env['res.config.settings']._fields['test_boolean_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: True

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, True], [('True', 'True'), (True, True)]),
            ([False, True], [('True', 'True'), (True, True)]),  # strange behavior
            ([True, True], [('True', 'True'), (True, 'True')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_boolean_field', res_config_setting_values, get_param_values)

    def test_integer_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 0], [(0, 0), ('0', '0'), (False, False)]),
            ([0, 0], [(0, 0), ('0', '0'), (False, False)]),
            ([1, 1], [(0, '1'), ('0', '1'), (False, '1')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_integer_field', res_config_setting_values, get_param_values)
        
        field = self.env['res.config.settings']._fields['test_integer_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 100

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 100], [(100, 100), ('100', '100')]),
            ([0, 100], [(100, 100), ('100', '100')]),
            ([1, 1], [(100, '1'), ('100', '1')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_integer_field', res_config_setting_values, get_param_values)

    def test_float_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 0], [(False, False), (0.0, 0.0), ('0.0', '0.0')]),
            ([0, 0], [(False, False), (0.0, 0.0), ('0.0', '0.0')]),
            ([1, 1], [(False, '1.0'), (0.0, '1.0'), ('0.0', '1.0')]),
            ([3.1415926, 3.14], [(False, '3.14'), (0.0, '3.14'), ('0.0', '3.14')]),
        ]
        for res_config_setting_values, get_param_values in test_values: 
            self._test_field('test_float_field', res_config_setting_values, get_param_values)

        field = self.env['res.config.settings']._fields['test_float_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 100.0

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 100.0], [(100.0, 100.0), ('100.0', '100.0')]),
            ([0, 100.0], [(100.0, 100.0), ('100.0', '100.0')]),
            ([1, 1], [(100.0, '1.0'), ('100.0', '1.0')]),
            ([3.1415926, 3.14], [(100.0, '3.14'), ('100.0', '3.14')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_float_field', res_config_setting_values, get_param_values)

    def test_char_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [(False, False), ('', '')]),
            (['', False], [(False, False), ('', '')]),
            ([False, False], [(False, False), ('', '')]),
            (['value', 'value'], [(False, 'value'), ('', 'value')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_param_values)

        field = self.env['res.config.settings']._fields['test_char_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: ''

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, ''], [(False, False), ('', '')]),
            (['', ''], [(False, False), ('', '')]),
            ([False, ''], [(False, False), ('', '')]),
            (['value', 'value'], [(False, 'value'), ('', 'value')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_param_values)

        field.default = lambda x: 'default'

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 'default'], [('default', 'default'), ('default', 'default')]),
            (['', 'default'], [('default', 'default'), ('default', 'default')]),
            ([False, 'default'], [('default', 'default'), ('default', 'default')]),
            (['value', 'value'], [('default', 'value'), ('default', 'value')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_param_values)

    def test_selection_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [(False, False)]),
            ([False, False], [(False, False)]),
            (['option2', 'option2'], [(False, 'option2')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_selection_field', res_config_setting_values, get_param_values)

        field = self.env['res.config.settings']._fields['test_selection_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 'option1'

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 'option1'], [('option1', 'option1')]),
            ([False, 'option1'], [('option1', 'option1')]),
            (['option2', 'option2'], [('option1', 'option2')]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_selection_field', res_config_setting_values, get_param_values)

    def test_many2one_field(self):
        """Test many2one field functionality"""
        falsy_partner = self.env['res.partner']
        partner = self.env['res.partner'].create({'name': 'Test Partner'})

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, falsy_partner], [(False, False)]),
            ([False, falsy_partner], [(False, False)]),
            ([falsy_partner, falsy_partner], [(False, False)]),
            ([partner.id, partner], [(False, str(partner.id))]),
            ([partner, partner], [(False, str(partner.id))]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_many2one_field', res_config_setting_values, get_param_values)

    @freeze_time(datetime(2024, 12, 31, 12, 0, 0))
    def test_datetime_field(self):
        test_datetime = datetime(2022, 1, 1, 12, 0, 0)

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [(False, False)]),
            ([False, False], [(False, False)]),
            ([test_datetime, test_datetime], [(False, str(test_datetime))]),
            ([str(test_datetime), test_datetime], [(False, str(test_datetime))]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_param_values)
        
        # static default
        field = self.env['res.config.settings']._fields['test_datetime_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        default_datetime = datetime(2023, 7, 7, 12, 0, 0)
        field.default = lambda x: default_datetime

        # [(res_config_write_value, res_config_set_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, default_datetime], [(default_datetime, default_datetime)]),
            ([False, default_datetime], [(default_datetime, default_datetime)]),
            ([test_datetime, test_datetime], [(default_datetime, str(test_datetime))]),
            ([str(test_datetime), test_datetime], [(default_datetime, str(test_datetime))]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_param_values)
        
        # dynamic default
        field.default = Datetime.now
        now = datetime(2024, 12, 31, 12, 0, 0)

        # [(res_config_write_value, res_config_get_value), [(get_param_default, get_param_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, now], [(now, now)]),
            ([False, now], [(now, now)]),
            ([test_datetime, test_datetime], [(now, str(test_datetime))]),
            ([str(test_datetime), test_datetime], [(now, str(test_datetime))]),
        ]
        for res_config_setting_values, get_param_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_param_values)
