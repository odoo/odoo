odoo.define('web.datepicker', function (require) {
"use strict";

var field_utils = require('web.field_utils');
var time = require('web.time');
var Widget = require('web.Widget');

var DateWidget = Widget.extend({
    template: "web.datepicker",
    type_of_date: "date",
    events: {
        'change.datetimepicker': 'changeDatetime',
        'show.datetimepicker': '_onShow',
        'click input.o_datepicker_input': '_onClick',
        'change .o_datepicker_input': 'changeDatetime',
        'input input': '_onInput',
    },
    /**
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.name = parent.name;
        this.options = _.extend({
            format : this.type_of_date === 'datetime' ? time.getLangDatetimeFormat() : time.getLangDateFormat(),
            minDate: moment({ y: 1900 }),
            maxDate: moment().add(200, "y"),
            useCurrent: false,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
                previous: 'fa fa-chevron-left',
                next: 'fa fa-chevron-right',
                today: 'fa fa-calendar-check-o',
                clear: 'fa fa-delete',
                close: 'fa fa-times'
            },
            calendarWeeks: true,
            buttons: {
                showToday: false,
                showClear: false,
                showClose: false,
            },
            widgetParent: 'body',
            keyBinds: null,
            allowInputToggle: true,
        }, options || {});
    },
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('input.o_datepicker_input');
        this.$input.focus(function (e) {
            e.stopImmediatePropagation();
        });
        this.__libInput = true;
        this.$input.datetimepicker(this.options);
        this.__libInput = false;
        this._setReadonly(false);
    },
    /**
     * @override
     */
    destroy: function () {
        this.__libInput = true;
        this.$input.datetimepicker('destroy');
        this.__libInput = false;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * set datetime value
     */
    changeDatetime: function () {
        if (this.isValid()) {
            var oldValue = this.getValue();
            this._setValueFromUi();
            var newValue = this.getValue();
            var hasChanged = !oldValue !== !newValue;
            if (oldValue && newValue) {
                var formattedOldValue = oldValue.format(time.getLangDatetimeFormat());
                var formattedNewValue = newValue.format(time.getLangDatetimeFormat());
                if (formattedNewValue !== formattedOldValue) {
                    hasChanged = true;
                }
            }
            if (hasChanged) {
                // The condition is strangely written; this is because the
                // values can be false/undefined
                this.trigger("datetime_changed");
            }
        }
    },
    /**
     * @returns {Moment|false}
     */
    getValue: function () {
        var value = this.get('value');
        return value && value.clone();
    },
    /**
     * @returns {boolean}
     */
    isValid: function () {
        var value = this.$input.val();
        if (value === "") {
            return true;
        } else {
            try {
                this._parseClient(value);
                return true;
            } catch (e) {
                return false;
            }
        }
    },
    /**
     * @param {Moment|false} value
     */
    setValue: function (value) {
        this.set({'value': value});
        var formatted_value = value ? this._formatClient(value) : null;
        this.$input.val(formatted_value);
        this.__libInput = true;
        this.$input.datetimepicker('date', value || null);
        this.__libInput = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Moment} v
     * @returns {string}
     */
    _formatClient: function (v) {
        return field_utils.format[this.type_of_date](v, null, {timezone: false});
    },
    /**
     * @private
     * @param {string|false} v
     * @returns {Moment}
     */
    _parseClient: function (v) {
        return field_utils.parse[this.type_of_date](v, null, {timezone: false});
    },
    /**
     * @private
     * @param {boolean} readonly
     */
    _setReadonly: function (readonly) {
        this.readonly = readonly;
        this.$input.prop('readonly', this.readonly);
    },
    /**
     * set the value from the input value
     *
     * @private
     */
    _setValueFromUi: function () {
        var value = this.$input.val() || false;
        this.setValue(this._parseClient(value));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function () {
        this.__libInput = true;
        this.$input.datetimepicker('toggle');
        this.__libInput = false;
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInput: function (ev) {
        if (this.__libInput) {
            ev.stopImmediatePropagation();
        }
    },
    /**
     * set the date of the picker by the current date or the today date
     *
     * @private
     */
    _onShow: function () {
        //when opening datetimepicker the date and time by default should be the one from
        //the input field if any or the current day otherwise
        if (this.$input.val().length !== 0 && this.isValid()) {
            var value = this._parseClient(this.$input.val());
            this.__libInput = true;
            this.$input.datetimepicker('date', value);
            this.__libInput = false;
            this.$input.select();
        }
    },
});

var DateTimeWidget = DateWidget.extend({
    type_of_date: "datetime",
    init: function (parent, options) {
        this._super(parent, _.extend({
            buttons: {
                showToday: false,
                showClear: false,
                showClose: true,
            },
        }, options || {}));
    },
});

return {
    DateWidget: DateWidget,
    DateTimeWidget: DateTimeWidget,
};

});
