odoo.define('hr_timesheet.timesheet_uom', function (require) {
'use strict';

const basicFields = require('web.basic_fields');
const fieldUtils = require('web.field_utils');

const fieldRegistry = require('web.field_registry');

const Timer = require('timer.Timer');

// We need the field registry to be populated, as we bind the
// timesheet_uom widget on existing field widgets.
require('web._field_registry');

const session = require('web.session');

/**
 * Extend the float factor widget to set default value for timesheet
 * use case. The 'factor' is forced to be the UoM timesheet
 * conversion from the session info.
 **/
const FieldTimesheetFactor = basicFields.FieldFloatFactor.extend({
    formatType: 'float_factor',
    /**
     * Override init to tweak options depending on the session_info
     *
     * @constructor
     * @override
     */
    init: function(parent, name, record, options) {
        this._super(parent, name, record, options);

        // force factor in format and parse options
        if (session.timesheet_uom_factor) {
            this.nodeOptions.factor = session.timesheet_uom_factor;
            this.parseOptions.factor = session.timesheet_uom_factor;
        }
    },
});


/**
 * Extend the float toggle widget to set default value for timesheet
 * use case. The 'range' is different from the default one of the
 * native widget, and the 'factor' is forced to be the UoM timesheet
 * conversion.
 **/
const FieldTimesheetToggle = basicFields.FieldFloatToggle.extend({
    formatType: 'float_factor',
    /**
     * Override init to tweak options depending on the session_info
     *
     * @constructor
     * @override
     */
    init: function(parent, name, record, options) {
        options = options || {};
        var fieldsInfo = record.fieldsInfo[options.viewType || 'default'];
        var attrs = options.attrs || (fieldsInfo && fieldsInfo[name]) || {};

        var hasRange = _.contains(_.keys(attrs.options || {}), 'range');

        this._super(parent, name, record, options);

        // Set the timesheet widget options: the range can be customized
        // by setting the option on the field in the view. The factor
        // is forced to be the UoM conversion factor.
        if (!hasRange) {
            this.nodeOptions.range = [0.00, 1.00, 0.50];
        }
        this.nodeOptions.factor = session.timesheet_uom_factor;
    },
});


/**
 * Extend float time widget to add the using of a timer for duration
 * (unit_amount) field.
 */
const FieldTimesheetTime = basicFields.FieldFloatTime.extend({
    init: function () {
        this._super.apply(this, arguments);

        if (session.timesheet_uom_factor) {
            this.nodeOptions.factor = session.timesheet_uom_factor;
            this.parseOptions.factor = session.timesheet_uom_factor;
        }
    },
    willstart() {
        const timePromise = this._rpc({
            model: 'timer.timer',
            method: 'get_server_time',
            args: []
        }).then((time) => {
            this.serverTime = time;
        });
        return Promise.all([
            this._super(...arguments),
            timePromise,
        ]);
    },

    _render: async function () {
        await this._super.apply(this, arguments);
        // Check if the timer_start exists and it's not false
        // In other word, when user clicks on play button, this button
        // launches the "action_timer_start".
        if (this.recordData.timer_start && !this.recordData.timer_pause) {
            this.time = Timer.createTimer(this.recordData.unit_amount, this.recordData.timer_start, this.serverTime);
            this._startTimeCounter();
        }
    },
    /**
     * @override
     */
    destroy: function () {
        clearTimeout(this.timer);
        this._super.apply(this, arguments);
    },
    _startTimeCounter: function () {
        if (this.time) {
            this.timer = setInterval(() => {
                this.time.addSecond();
                this.$el.text(this.time.toString());
                this.$el.addClass('font-weight-bold text-danger');
            }, 1000);
        } else {
            clearTimeout(this.timer);
            this.$el.removeClass('font-weight-bold text-danger');
        }
    },
});


/**
 * Binding depending on Company Preference
 *
 * determine wich widget will be the timesheet one.
 * Simply match the 'timesheet_uom' widget key with the correct
 * implementation (float_time, float_toggle, ...). The default
 * value will be 'float_factor'.
**/
const widgetName = 'timesheet_uom' in session ?
         session.timesheet_uom.timesheet_widget : 'float_factor';

let FieldTimesheetUom = null;

if (widgetName === 'float_toggle') {
    FieldTimesheetUom = FieldTimesheetToggle;
} else if (widgetName === 'float_time') {
    FieldTimesheetUom = FieldTimesheetTime;
} else {
    FieldTimesheetUom = (
            fieldRegistry.get(widgetName) &&
            fieldRegistry.get(widgetName).extend({})
        ) || FieldTimesheetFactor;
}

fieldRegistry.add('timesheet_uom', FieldTimesheetUom);


// bind the formatter and parser method, and tweak the options
const _tweak_options = function(options) {
    if (!_.contains(options, 'factor')) {
        options.factor = session.timesheet_uom_factor;
    }
    return options;
};

fieldUtils.format.timesheet_uom = function(value, field, options) {
    options = _tweak_options(options || {});
    const formatter = fieldUtils.format[FieldTimesheetUom.prototype.formatType];
    return formatter(value, field, options);
};

fieldUtils.parse.timesheet_uom = function(value, field, options) {
    options = _tweak_options(options || {});
    const parser = fieldUtils.parse[FieldTimesheetUom.prototype.formatType];
    return parser(value, field, options);
};

return {
    FieldTimesheetUom,
    FieldTimesheetFactor,
    FieldTimesheetTime,
    FieldTimesheetToggle
};

});
