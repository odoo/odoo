odoo.define('hr_attendance.kiosk_confirm', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var QWeb = core.qweb;


var KioskConfirm = AbstractAction.extend({
    events: {
        "click .o_hr_attendance_back_button": function () { this.do_action(this.next_action, {clear_breadcrumbs: true}); },
        "click .o_hr_attendance_sign_in_out_icon": function () {
            var self = this;
            this.$('.o_hr_attendance_sign_in_out_icon').attr("disabled", "disabled");
            this._rpc({
                    model: 'hr.employee',
                    method: 'attendance_manual',
                    args: [[this.employee_id], this.next_action],
                })
                .then(function(result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                        self.$('.o_hr_attendance_sign_in_out_icon').removeAttr("disabled");
                    }
                });
        },
        'click .o_hr_attendance_pin_pad_button_0': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 0); },
        'click .o_hr_attendance_pin_pad_button_1': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 1); },
        'click .o_hr_attendance_pin_pad_button_2': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 2); },
        'click .o_hr_attendance_pin_pad_button_3': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 3); },
        'click .o_hr_attendance_pin_pad_button_4': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 4); },
        'click .o_hr_attendance_pin_pad_button_5': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 5); },
        'click .o_hr_attendance_pin_pad_button_6': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 6); },
        'click .o_hr_attendance_pin_pad_button_7': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 7); },
        'click .o_hr_attendance_pin_pad_button_8': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 8); },
        'click .o_hr_attendance_pin_pad_button_9': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 9); },
        'click .o_hr_attendance_pin_pad_button_C': function() { this.$('.o_hr_attendance_PINbox').val(''); },
        'click .o_hr_attendance_pin_pad_button_ok': function() {
            var self = this;
            this.$('.o_hr_attendance_pin_pad_button_ok').attr("disabled", "disabled");
            this._rpc({
                    model: 'hr.employee',
                    method: 'attendance_manual',
                    args: [[this.employee_id], this.next_action, this.$('.o_hr_attendance_PINbox').val()],
                })
                .then(function(result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                        self.$('.o_hr_attendance_PINbox').val('');
                        setTimeout( function() { self.$('.o_hr_attendance_pin_pad_button_ok').removeAttr("disabled"); }, 500);
                    }
                });
        },
    },

    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.next_action = 'hr_attendance.hr_attendance_action_kiosk_mode';
        this.employee_id = action.employee_id;
        this.employee_name = action.employee_name;
        this.employee_state = action.employee_state;
    },

    start: function () {
        var self = this;
        this.getSession().user_has_group('hr_attendance.group_hr_attendance_use_pin').then(function(has_group){
            self.use_pin = has_group;
            self.$el.html(QWeb.render("HrAttendanceKioskConfirm", {widget: self}));
            self.start_clock();
        });
        return self._super.apply(this, arguments);
    },

    start_clock: function () {
        this.clock_start = setInterval(function() {this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
    },

    destroy: function () {
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('hr_attendance_kiosk_confirm', KioskConfirm);

return KioskConfirm;

});
