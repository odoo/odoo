/**
 * Defines a proper password field (rather than just an InputField option) to
 * provide a "password strength" meter based on the database's current
 * policy & the 2word16 password policy recommended by Shay (2016) "Designing
 * Password Policies for Strength and Usability".
 */
odoo.define('auth_password_policy.PasswordField', function (require) {
"use strict";
var fields = require('web.basic_fields');
var registry = require('web.field_registry');
var policy = require('auth_password_policy');
var Meter = require('auth_password_policy.Meter');
var _formatValue = require('web.AbstractField').prototype._formatValue;

var PasswordField = fields.InputField.extend({
    className: 'o_field_password',

    init: function () {
        this._super.apply(this, arguments);
        this.nodeOptions.isPassword = true;
        this._meter = new Meter(this, new policy.Policy({}), policy.recommendations);
    },
    willStart: function () {
        var _this = this;
        var getPolicy = this._rpc({
            model: 'res.users',
            method: 'get_password_policy',
        }).then(function (p) {
            _this._meter = new Meter(_this, new policy.Policy(p), policy.recommendations);
        });
        return $.when(
            this._super.apply(this, arguments),
            getPolicy
        );
    },
    /**
     * Add a <meter> next to the input (TODO: move to template?)
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        var _this = this;
        var meter = this._meter;
        return $.when(this._super.apply(this, arguments)).then(function () {
            return meter._widgetRenderAndInsert(function (t) {
                // insertAfter doesn't work and appendTo means the meter is
                // ignored (as this.$el is an input[type=password])
                _this.$el = t.add(meter.$el);
            }, _this.$el);
        }).then(function () {
            // initial meter update when re-editing
            meter.update(_this._getValue());
        });
    },
    /**
     * disable formatting for this widget, or the value gets replaced by
     * **** before being written back into the widget when switching from
     * readonly to editable (so input -> readonly -> input more, the 1st input
     * is all replaced by *s not just in display but in actual storage)
     *
     * @override
     * @private
     */
    _formatValue: function (value) { return value || ''; },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(_formatValue.call(this, this.value));
    },
    /**
     * Update meter value on the fly on value change
     *
     * @override
     * @private
     */
    _onInput: function () {
        this._super();
        this._meter.update(this._getValue());
    }
});

registry.add("password_meter", PasswordField);
return PasswordField;
});
