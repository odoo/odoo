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

    def _test_field(self, field_name, res_config_setting_values, get_values):
        ResConfigSettings = self.env['res.config.settings']
        IrConfigParameter = self.env['ir.config_parameter']
        field = ResConfigSettings._fields[field_name]
        config_parameter = field.config_parameter

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

        match field.type:
            case 'boolean':
                get_type_ = IrConfigParameter.get_bool
            case 'integer' | 'many2one':
                get_type_ = IrConfigParameter.get_int
            case 'float':
                get_type_ = IrConfigParameter.get_float
            case 'char' | 'selection' | 'datetime':
                get_type_ = IrConfigParameter.get_str
            case _:
                raise ValueError(f"Not supported field type: {field.type} for the test")

        # ir.config_parameter: get_str/get_int/get_float/get_bool
        def get_type(default):
            return get_type_(config_parameter, default)

        for get_type_default, get_type_value in get_values:
            if get_type_value is False:
                self.assertIs(get_type(get_type_default), False)
            else:
                self.assertEqual(get_type(get_type_default), get_type_value)

    def test_boolean_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [(False, False)]),
            ([False, False], [(False, False)]),
            ([True, True], [(False, True)]),
        ]

        for res_config_setting_values, get_values in test_values:
            self._test_field('test_boolean_field', res_config_setting_values, get_values)

        field = self.env['res.config.settings']._fields['test_boolean_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: True

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, True], [(True, True)]),
            ([False, False], [(True, False)]),
            ([True, True], [(True, True)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_boolean_field', res_config_setting_values, get_values)

    def test_integer_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 0], [(0, 0)]),
            ([0, 0], [(0, 0)]),
            ([1, 1], [(0, 1)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_integer_field', res_config_setting_values, get_values)

        field = self.env['res.config.settings']._fields['test_integer_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 100

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 100], [(100, 100)]),
            ([0, 0], [(100, 0)]),
            ([1, 1], [(100, 1)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_integer_field', res_config_setting_values, get_values)

    def test_float_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 0], [(0, 0)]),
            ([0, 0], [(0, 0)]),
            ([1, 1], [(0, 1)]),
            ([3.1415926, 3.14], [(0, 3.14)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_float_field', res_config_setting_values, get_values)

        field = self.env['res.config.settings']._fields['test_float_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 100.0

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 100.0], [(100, 100)]),
            ([0, 0], [(100, 0)]),
            ([1, 1], [(100, 1)]),
            ([3.1415926, 3.14], [(100, 3.14)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_float_field', res_config_setting_values, get_values)

    def test_char_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [('', '')]),
            (['', ''], [('', '')]),
            ([False, False], [('', '')]),
            (['value', 'value'], [('', 'value')]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_values)

        field = self.env['res.config.settings']._fields['test_char_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: ''

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, ''], [('', '')]),
            (['', ''], [('', '')]),
            ([False, ''], [('', '')]),
            (['value', 'value'], [('', 'value')]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_values)

        field.default = lambda x: 'default'

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 'default'], [('default', 'default')]),
            (['', ''], [('default', '')]),
            ([False, 'default'], [('default', 'default')]),
            (['value', 'value'], [('default', 'value')]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_char_field', res_config_setting_values, get_values)

    def test_selection_field(self):
        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [('', '')]),
            ([False, False], [('', '')]),
            (['option2', 'option2'], [('', 'option2')]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_selection_field', res_config_setting_values, get_values)

        field = self.env['res.config.settings']._fields['test_selection_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        field.default = lambda x: 'option1'

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, 'option1'], [('option1', 'option1')]),
            ([False, 'option1'], [('option1', 'option1')]),
            (['option2', 'option2'], [('option1', 'option2')]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_selection_field', res_config_setting_values, get_values)

    def test_many2one_field(self):
        """Test many2one field functionality"""
        falsy_partner = self.env['res.partner']
        partner = self.env['res.partner'].create({'name': 'Test Partner'})

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, falsy_partner], [(0, 0)]),
            ([False, falsy_partner], [(0, 0)]),
            ([falsy_partner, falsy_partner], [(0, 0)]),
            ([partner.id, partner], [(0, partner.id)]),
            ([partner, partner], [(0, partner.id)]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_many2one_field', res_config_setting_values, get_values)

    @freeze_time(datetime(2024, 12, 31, 12, 0, 0))
    def test_datetime_field(self):
        test_datetime = datetime(2022, 1, 1, 12, 0, 0)

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, False], [('', '')]),
            ([False, False], [('', '')]),
            ([test_datetime, test_datetime], [('', str(test_datetime))]),
            ([str(test_datetime), test_datetime], [('', str(test_datetime))]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_values)

        # static default
        field = self.env['res.config.settings']._fields['test_datetime_field']
        old_default = field.default
        self.addCleanup(setattr, field, 'default', old_default)
        default_datetime = datetime(2023, 7, 7, 12, 0, 0)
        field.default = lambda x: default_datetime

        # [(res_config_write_value, res_config_set_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, default_datetime], [(str(default_datetime), str(default_datetime))]),
            ([False, default_datetime], [(str(default_datetime), str(default_datetime))]),
            ([test_datetime, test_datetime], [(str(default_datetime), str(test_datetime))]),
            ([str(test_datetime), test_datetime], [(str(default_datetime), str(test_datetime))]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_values)

        # dynamic default
        field.default = Datetime.now
        now = datetime(2024, 12, 31, 12, 0, 0)

        # [(res_config_write_value, res_config_get_value), [(get_type_default, get_type_value), ...]]
        test_values = [
            ([DEFAULT_SETTING, now], [(str(now), str(now))]),
            ([False, now], [(str(now), str(now))]),
            ([test_datetime, test_datetime], [(str(now), str(test_datetime))]),
            ([str(test_datetime), test_datetime], [(str(now), str(test_datetime))]),
        ]
        for res_config_setting_values, get_values in test_values:
            self._test_field('test_datetime_field', res_config_setting_values, get_values)
