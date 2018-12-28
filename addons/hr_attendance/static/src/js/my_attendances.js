odoo.define('hr_attendance.my_attendances', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');


var MyAttendances = AbstractAction.extend({
    contentTemplate: 'HrAttendanceMyMainMenu',
    events: {
        "click .o_hr_attendance_sign_in_out_icon": function() {
            this.$('.o_hr_attendance_sign_in_out_icon').attr("disabled", "disabled");
            this.update_attendance();
        },
    },

    willStart: function () {
        var self = this;

        var def = this._rpc({
                model: 'hr.employee',
                method: 'search_read',
                args: [[['user_id', '=', this.getSession().uid]], ['attendance_state', 'name']],
            })
            .then(function (res) {
                self.employee = res.length && res[0];
            });

        return $.when(def, this._super.apply(this, arguments));
    },

    update_attendance: function () {
        var self = this;
        this._rpc({
                model: 'hr.employee',
                method: 'attendance_manual',
                args: [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
            })
            .then(function(result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                }
            });
    },
});

core.action_registry.add('hr_attendance_my_attendances', MyAttendances);

return MyAttendances;

});
