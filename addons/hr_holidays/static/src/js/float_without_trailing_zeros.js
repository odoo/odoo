/** @odoo-module **/
import FieldRegistry from 'web.field_registry';
odoo.define('hr_holidays.FloatWithoutTrailingZeros', function (require) {
    "use strict";
    var basic_fields = require('web.basic_fields');
    var FieldFloat = basic_fields.FieldFloat;

    var FloatWithoutTrailingZeros = FieldFloat.extend({
            _renderReadonly: function () {
                var value = this._formatValue(this.value);
                var parsed_value = parseFloat(value);
                value = parsed_value.toString().replace(/\.0+$/, '');
                this.$el.text(value);
            },
        });

    FieldRegistry.add('float_without_trailing_zeros', FloatWithoutTrailingZeros);
});
