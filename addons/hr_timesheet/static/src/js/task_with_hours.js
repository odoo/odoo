odoo.define('hr_timesheet.task_with_hours', function (require) {
"use strict";

var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');
var FieldMany2One = relational_fields.FieldMany2One;

var TaskWithHours = FieldMany2One.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.additionalContext.hr_timesheet_display_remaining_hours = true;
    },
    /**
     * @override
     */
    _getDisplayNameWithoutHours: function (value) {
        return value.split(' ‒ ')[0];
    },
    /**
     * @override
     * @private
     */
    _renderEdit: function (){
        this.m2o_value = this._getDisplayNameWithoutHours(this.m2o_value);
        this._super.apply(this, arguments);
    },
});

field_registry.add('task_with_hours', TaskWithHours);

return TaskWithHours;

});