odoo.define('hr_attendance.field_widget', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;


var PresenceIndicator = AbstractField.extend({
    template: 'PresenceIndicator',

    start: function() {
        this.$el.tooltip({title: _t("Employee Presence<br/>Green: checked in<br/>Red: checked out"), trigger: 'hover'});
        return this._super();
    },
    render: function() {
        this.$el.toggleClass("oe_hr_attendance_status_green", this.value === 'checked_in');
        this.$el.toggleClass("oe_hr_attendance_status_red", this.value === 'checked_out');
    },
    is_set: function() {
        return true;
    }
});

field_registry.add('hr_attendance_form_presence_indicator', PresenceIndicator);

});
