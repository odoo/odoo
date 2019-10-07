odoo.define('hr_timesheet.timesheet_uom', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var basicFields = require('web.basic_fields');
var fieldUtils = require('web.field_utils');

var fieldRegistry = require('web.field_registry');
var _registry = require('web._field_registry');  // wait registry to be filled...
var session = require('web.session');

/**
 * Extend the float factor widget to set default value for timesheet
 * use case. The 'factor' is forced to be the UoM timesheet
 * conversion from the session info.
 **/
var FieldTimesheetFactor = basicFields.FieldFloatFactor.extend({
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
var FieldTimesheetToggle = basicFields.FieldFloatToggle.extend({
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
 * Binding depending on Company Preference
 *
 * determine wich widget will be the timesheet one.
 * Simply match the 'timesheet_uom' widget key with the correct
 * implementation (float_time, float_toggle, ...). The default
 * value will be 'float_factor'.
**/
var widgetName = 'timesheet_uom' in session ?
         session.timesheet_uom.timesheet_widget : 'float_factor';
var FieldTimesheetUom = widgetName === 'float_toggle' ?
         FieldTimesheetToggle : (fieldRegistry.get(widgetName) || FieldTimesheetFactor);

fieldRegistry.add('timesheet_uom', FieldTimesheetUom);


// bind the formatter and parser method, and tweak the options
var _tweak_options = function(options) {
    if (!_.contains(options, 'factor')) {
        options.factor = session.timesheet_uom_factor;
    }
    return options;
};

fieldUtils.format.timesheet_uom = function(value, field, options) {
    options = _tweak_options(options || {});
    var formatter = fieldUtils.format[FieldTimesheetUom.prototype.formatType];
    return formatter(value, field, options);
};

fieldUtils.parse.timesheet_uom = function(value, field, options) {
    options = _tweak_options(options || {});
    var parser = fieldUtils.parse[FieldTimesheetUom.prototype.formatType];
    return parser(value, field, options);
};

return FieldTimesheetUom;
});
