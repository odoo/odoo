odoo.define('hr_attendance.Message', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');

var _t = core._t;


var Message = Widget.extend({
    template: 'HrAttendanceMessage',

    events: {
        "click .o_hr_attendance_button_dismiss": function () { this.do_action(this.next_action, {clear_breadcrumbs: true}); },
    },

    init: function(parent, action) {
        this._super.apply(this, arguments);
        var self = this;
        var default_action = { type: "ir.actions.client", name: 'Attendances', tag: 'hr_attendance_my_main_menu', params: {} };
        if(!action.attendance){
            self.session.user_has_group('base.group_hr_user').then(function(has_group){
                if(has_group){
                    self.next_action = { type: "ir.actions.client", name: 'Attendances', tag: 'hr_attendance_main_menu', target: 'fullscreen', params: {} };
                }
            });
            return;
        }
        this.next_action = action.next_action || default_action;
        this.attendance = action.attendance;
        this.attendance.check_in_time = (new Date((new Date(this.attendance.check_in)).valueOf() - (new Date()).getTimezoneOffset()*60*1000)).toTimeString().slice(0,8);
        this.attendance.check_out_time = this.attendance.check_out && (new Date((new Date(this.attendance.check_out)).valueOf() - (new Date()).getTimezoneOffset()*60*1000)).toTimeString().slice(0,8);
        this.previous_attendance_change_date = action.previous_attendance_change_date;
        this.employee_name = action.employee_name;
    },

    start: function() {
        if (!this.attendance){
            return;
        }
        if (this.attendance.check_out) {
            this.farewell_message();
        } else {
            this.welcome_message();
        }
    },

    welcome_message: function() {
        var self = this;
        var now = new Date((new Date(this.attendance.check_in)).valueOf() - (new Date()).getTimezoneOffset()*60*1000);
        self.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);

        if(now.getHours()<5){
            self.$('.o_hr_attendance_message_message').append(_t("Good night"));
        } else if(now.getHours() < 12){
            if(now.getHours() < 8 && Math.random() < .3){
                if(Math.random()<.75){
                    self.$('.o_hr_attendance_message_message').append(_t("The early bird catches the worm"));
                } else {
                    self.$('.o_hr_attendance_message_message').append(_t("First come, first served"));
                }
                
            } else {
                self.$('.o_hr_attendance_message_message').append(_t("Good morning"));
            }
        } else if(now.getHours()<17){
            self.$('.o_hr_attendance_message_message').append(_t("Good afternoon"));
        } else if(now.getHours()<23){
            self.$('.o_hr_attendance_message_message').append(_t("Good evening"));
        } else {
            self.$('.o_hr_attendance_message_message').append(_t("Good night"));
        }
        if(this.previous_attendance_change_date){
            var last_check_out_date = new Date((new Date(this.previous_attendance_change_date)).valueOf() - (new Date()).getTimezoneOffset()*60*1000);
            if(now.valueOf() - last_check_out_date.valueOf() > 1000*60*60*24*7){
                self.$('.o_hr_attendance_random_message').html(_t("Glad to have you back, it's been a while!"));
            } else {
                if(Math.random() < .02){
                    self.$('.o_hr_attendance_random_message').html(_t("If a job is worth doing, it is worth doing well!"));
                }
            }
        }
    },

    farewell_message: function() {
        var self = this;
        var now = new Date((new Date(this.attendance.check_out)).valueOf() - (new Date()).getTimezoneOffset()*60*1000);
        self.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);

        if(this.previous_attendance_change_date){
            var last_check_in_date = new Date((new Date(this.previous_attendance_change_date)).valueOf() - (new Date()).getTimezoneOffset()*60*1000);
            if(now.valueOf() - last_check_in_date.valueOf() > 1000*60*60*12){
                self.$('.o_hr_attendance_warning_message').append(_t("Warning! Last check in was over 12 hours ago.<br/>If this isn't right, please contact Human Resources."));
                clearTimeout(self.return_to_main_menu);
            } else if(now.valueOf() - last_check_in_date.valueOf() > 1000*60*60*8){
                self.$('.o_hr_attendance_random_message').html(_t("Another good day's work! See you soon!"));
            }
        }

        if(now.getHours()<12){
            self.$('.o_hr_attendance_message_message').append(_t("Have a good day!"));
        } else if(now.getHours()<14){
            self.$('.o_hr_attendance_message_message').append(_t("Have a nice lunch!"));
            if(Math.random() < 0.05){
                self.$('.o_hr_attendance_random_message').html(_t("Eat breakfast as a king, lunch as a merchant and supper as a beggar"));
            } else if(Math.random() < 0.06){
                self.$('.o_hr_attendance_random_message').html(_t("An apple a day keeps the doctor away"));
            }
        } else if(now.getHours()<17){
            self.$('.o_hr_attendance_message_message').append(_t("Have a good afternoon"));
        } else {
            if(now.getHours()<18 && Math.random()<0.2){
                self.$('.o_hr_attendance_message_message').append(_t("Early to bed and early to rise, makes a man healthy, wealthy and wise"));
            } else {
                self.$('.o_hr_attendance_message_message').append(_t("Have a good evening"));
            }
        }
    },

    destroy: function () {
        clearTimeout(this.return_to_main_menu);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('hr_attendance_message', Message);

return Message;

});
