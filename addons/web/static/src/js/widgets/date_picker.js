odoo.define('web.datepicker', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var time = require('web.time');
var Widget = require('web.Widget');

var _t = core._t;

var DateWidget = Widget.extend({
    template: "web.datepicker",
    type_of_date: "date",
    events: {
        'dp.change': 'changeDatetime',
        'dp.show': '_onShow',
        'change .o_datepicker_input': 'changeDatetime',
    },
    /**
     * @override
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        var l10n = _t.database.parameters;

        this.name = parent.name;
        this.options = _.defaults(options || {}, {
            format : this.type_of_date === 'datetime' ? time.getLangDatetimeFormat() : time.getLangDateFormat(),
            minDate: moment({ y: 1900 }),
            maxDate: moment().add(200, "y"),
            calendarWeeks: true,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
                close: 'fa fa-times',
            },
            locale : moment.locale(),
            allowInputToggle: true,
            keyBinds: null,
            widgetParent: 'body',
            useCurrent: false,
        });
    },
    /**
     * @override
     */
    start: function() {
        this.$input = this.$('input.o_datepicker_input');
        this.$input.focus(function(e) {
            e.stopImmediatePropagation();
        });
        this.$input.datetimepicker(this.options);
        this.picker = this.$input.data('DateTimePicker');
        this.$input.click(this.picker.toggle.bind(this.picker));
        this._setReadonly(false);
    },
    /**
     * @override
     */
    destroy: function() {
        this.picker.destroy();
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

            if (!oldValue !== !newValue || oldValue && newValue && !oldValue.isSame(newValue)) {
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
        if(value === "") {
            return true;
        } else {
            try {
                this._parseClient(value);
                return true;
            } catch(e) {
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
        if (this.picker) {
            this.picker.date(value || null);
        }
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
    _setValueFromUi: function() {
        var value = this.$input.val() || false;
        this.setValue(this._parseClient(value));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * set the date of the picker by the current date or the today date
     *
     * @private
     */
    _onShow: function () {
        //when opening datetimepicker the date and time by default should be the one from
        //the input field if any or the current day otherwise
        if(this.$input.val().length !== 0 && this.isValid()) {
            var value = this._parseClient(this.$input.val());
            this.picker.date(value);
            this.$input.select();
        }
    },
});

var DateTimeWidget = DateWidget.extend({
    type_of_date: "datetime",
    init: function() {
        this._super.apply(this, arguments);
        this.options = _.defaults(this.options, {
            showClose: true,
        });
    },
});

return {
    DateWidget: DateWidget,
    DateTimeWidget: DateTimeWidget,
};

});
