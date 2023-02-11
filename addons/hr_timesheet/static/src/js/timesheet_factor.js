odoo.define('hr_timesheet.timesheet_factor', function (require) {
'use strict';

const timesheetUomFields = require('hr_timesheet.timesheet_uom');
const fieldUtils = require('web.field_utils');
const fieldRegistry = require('web.field_registry');

fieldRegistry.add('timesheet_factor', timesheetUomFields.FieldTimesheetFactor);

fieldUtils.format.timesheet_factor = function(value, field, options) {
    const formatter = fieldUtils.format[timesheetUomFields.FieldTimesheetFactor.prototype.formatType];
    return formatter(value, field, options);
};

fieldUtils.parse.timesheet_factor = function(value, field, options) {
    const parser = fieldUtils.parse[timesheetUomFields.FieldTimesheetFactor.prototype.formatType];
    return parser(value, field, options);
};

});
