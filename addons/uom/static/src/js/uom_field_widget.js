odoo.define('uom.UomFieldWidget', function (require) {
    "use strict";

    const basic_fields = require('web.basic_fields');
    const core = require('web.core');
    const fieldUtils = require('web.field_utils');
    const field_registry = require('web.field_registry');
    const session = require('web.session');
    const utils = require('web.utils');

    const _t = core._t;
    const FieldFloat = basic_fields.FieldFloat;
    const InputField = basic_fields.InputField;

    const FieldMeasure = FieldFloat.extend({
        supportedFieldTypes: ['float', 'measure'],
        resetOnAnyFieldChange: true,  // TODO: only listen to uom field's change, but how?

        events: Object.assign({}, InputField.prototype.events, {
            input: '_onInput',
        }),

        /**
         * Float fields using a measure widget have an additional uom_field
         * parameter which defines the name of the field from which the uom
         * should be read.
         *
         * If no uom field is given or the field does not exist, we fallback
         * to the default input behavior instead.
         *
         * @override
         */
        init: function () {
            this._super(...arguments);
            this._setUom();
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Re-gets the uom as its value may have changed.
         * @see FieldUom.resetOnAnyFieldChange
         *
         * @override
         * @private
         */
        _reset: function () {
            this._super(...arguments);
            this._setUom();
        },

        /**
         * Deduces the uom description from the field options and view state.
         * The description is then available at this.uom.
         *
         * @private
         */
        _setUom: function () {
            const uomField = this.nodeOptions.uom_field || this.field.uom_field || 'uom_id' || 'x_uom_id';
            const uomID = this.record.data[uomField] && this.record.data[uomField].res_id;
            this.uom = session.uoms[uomID];
            this.formatOptions.uom = this.uom; // _formatValue() uses formatOptions
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Allow to enter decimal digits base on the uom's rounding value.
         *
         * @override
         * @private
         */
        _onInput: function() {
            this._super(...arguments);
            const value = this.$input.val();
            const uom_precision = this.formatOptions.uom && this.formatOptions.uom.decimal_places;
            if (value.includes('.')) {
                const precision = value.split('.')[1].length;
                if (uom_precision < precision) {
                    this.do_warn(_.str.sprintf(_t('Only %s decimals are allowed.</br> This setting can be configured on the Unit of Measure.'), uom_precision));
                    this.$input.val(value.slice(0, -(precision - uom_precision)));
                    return;
                }
            }

            const uom_rounding = this.formatOptions.uom && this.formatOptions.uom.rounding;
            const rounded = utils.round_precision(value, uom_rounding);
            if (! utils.float_is_zero(parseFloat(value) - rounded, 13)) {
                this.do_warn(_.str.sprintf(_t('The rounding %s is not respected.</br> This setting can be configured on the Unit of Measure.'), uom_rounding));
            }
        },
    });
    field_registry.add('measure', FieldMeasure);

    /**
     * Returns a string representing a float.  The result takes into account the
     * user settings (to display the correct decimal separator).
     *
     * @param {float|false} value the value that should be formatted
     * @param {Object} [field] a description of the field (returned by fields_get
     *   for example).  It may contain a description of the number of digits that
     *   should be used.
     * @param {Object} [options] additional options to override the values in the
     *   python description of the field.
     * @param {Object} [options.uom] the description of the uom to use
     * @param {integer} [options.uom_id]
     *        the id of the 'uom.uom' to use (ignored if options.uom)
     * @param {string} [options.uom_field]
     *        the name of the field whose value is the uom id
     *        (ignore if options.uom or options.uom_id)
     *        Note: if not given it will default to the field uom_field value
     *        or to 'uom_id'.
     * @param {Object} [options.data]
     *        a mapping of field name to field value, required with
     *        options.uom_field
     * @returns {string}
     */
    fieldUtils.format.measure = function(value, field, options) {
        options = options || {};
        if (value === false) {
            return "";
        }
        let uom = options.uom;
        if (!uom) {
            let uom_id = options.uom_id;
            const uom_field = options.uom_field || field.uom_field || 'uom_id';
            if (!uom_id && options.data) {
                uom_id = options.data[uom_field] && options.data[uom_field].res_id;
            } else if (!uom_id && options[uom_field]) {
                uom_id = options[uom_field].res_id;
            }
            uom = session.uoms[uom_id];
        }

        const l10n = core._t.database.parameters;
        const precision = (uom && uom.decimal_places) || 0;
        const formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
        formatted[0] = utils.insert_thousand_seps(formatted[0]);
        return formatted.join(l10n.decimal_point);
    };

    fieldUtils.parse.measure = fieldUtils.parse.float;
});

