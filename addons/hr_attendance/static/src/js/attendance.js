odoo.define('hr_attendance.hr_attendance', function(require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var formats = require('web.formats');
var Model = require('web.DataModel');
var SystrayMenu = require('web.SystrayMenu');
var time = require('web.time');
var Widget = require('web.Widget');

var _t = core._t;

var AttendanceSlider = Widget.extend({
    template: 'AttendanceSlider',
    init: function (parent) {
        this._super(parent);
        this.set({"signed_in": false});
    },
    start: function() {
        var self = this;
        var tmp = function() {
            var $sign_in_out_icon = this.$('#oe_attendance_sign_in_out_icon');
            $sign_in_out_icon.toggleClass("fa-sign-in", ! this.get("signed_in"));
            $sign_in_out_icon.toggleClass("fa-sign-out", this.get("signed_in"));
        };
        this.on("change:signed_in", this, tmp);
        _.bind(tmp, this)();
        this.$(".oe_attendance_sign_in_out").click(function(ev) {
            ev.preventDefault();
            self.do_update_attendance();
        });
        this.$el.tooltip({
            title: function() {
                var last_text = formats.format_value(self.last_sign, {type: "datetime"});
                var current_text = formats.format_value(new Date(), {type: "datetime"});
                var duration = self.last_sign ? $.timeago(self.last_sign) : "none";
                if (self.get("signed_in")) {
                    return _.str.sprintf(_t("Last sign in: %s,<br />%s.<br />Click to sign out."), last_text, duration);
                } else {
                    return _.str.sprintf(_t("Click to Sign In at %s."), current_text);
                }
            },
        });
        return this.check_attendance();
    },
    do_update_attendance: function () {
        var self = this;
        var hr_employee = new data.DataSet(self, 'hr.employee');
        hr_employee.call('attendance_action_change', [
            [self.employee.id]
        ]).done(function (result) {
            self.last_sign = new Date();
            self.set({"signed_in": ! self.get("signed_in")});
        });
    },
    check_attendance: function () {
        var self = this;
        self.employee = false;
        this.$el.hide();
        var employee = new data.DataSetSearch(self, 'hr.employee', self.session.user_context, [
            ['user_id', '=', self.session.uid]
        ]);
        return employee.read_slice(['id', 'name', 'state', 'last_sign', 'attendance_access']).then(function (res) {
            if (_.isEmpty(res) )
                return;
            if (res[0].attendance_access === false){
                return;
            }
            self.$el.show();
            self.employee = res[0];
            self.last_sign = time.str_to_datetime(self.employee.last_sign);
            self.set({"signed_in": self.employee.state !== "absent"});
        });
    },
});

// Put the AttendanceSlider widget in the systray menu if the user is an employee
var Users = new Model('res.users');
Users.call('has_group', ['base.group_user']).done(function(is_employee) {
    if (is_employee) {
        SystrayMenu.Items.push(AttendanceSlider);
    }
});

});
