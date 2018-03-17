odoo.define('school_attendance.my_attendances', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;


var MyAttendances = Widget.extend({
    events: {
        "click .o_school_attendance_sign_in_out_icon": function() {
            this.$('.o_school_attendance_sign_in_out_icon').attr("disabled", "disabled");
            this.update_attendance();
        },
    },

    start: function () {
        var self = this;

        var school_student = new Model('school.student');
        school_student.query(['attendance_state', 'name'])
            .filter([['user_id', '=', self.session.uid]])
            .all()
            .then(function (res) {
                if (_.isEmpty(res) ) {
                    self.$('.o_school_attendance_student').append(_t("Error : Could not find student linked to user"));
                    return;
                }
                self.student = res[0];
                self.$el.html(QWeb.render("SchoolAttendanceMyMainMenu", {widget: self}));
            });

        return this._super.apply(this, arguments);
    },

    update_attendance: function () {
        var self = this;
        var school_student = new Model('school.student');
        school_student.call('attendance_manual', [[self.student.id], 'school_attendance.school_attendance_action_my_attendances'])
            .then(function(result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                }
            });
    },
});

core.action_registry.add('school_attendance_my_attendances', MyAttendances);

return MyAttendances;

});
