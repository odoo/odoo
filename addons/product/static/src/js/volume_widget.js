odoo.define('product.volume_widget', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

var FieldVolume = basicFields.MeasureField.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * FieldVolume overrides _formatValue to apply unit conversion.
     * Volumes are always stored in liters, converted to the company's UoM.
     *
     * @override
     * @private
     */
    _formatValue: function (value) {
        value = value * this.measure.factor;
        return this._super(value);
    },
    /**
     * Intercept the parsed value to apply the UoM factor conversion.
     *
     * @override
     * @private
     */
    _parseValue: function (value) {
        var parsed_value = this._super.apply(this, arguments);
        return parsed_value / this.measure.factor;
    },
    /**
     * Deduces the measure description from the user session.
     * The description is then available at this.measure.
     *
     * @override
     * @private
     */
    _setMeasure: function () {
        this.measure = this.getSession().volume_uom;
        if (this.field.digits) {
            this.measure.digits = this.field.digits;
        }
    },
});

fieldRegistry.add('volume', FieldVolume);

});
