odoo.define('hr_attendance.greeting_message', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var time = require('web.time');
var field_utils = require('web.field_utils');

var _t = core._t;


var GreetingMessage = AbstractAction.extend({
    contentTemplate: 'HrAttendanceGreetingMessage',

    events: {
        "click .o_hr_attendance_button_dismiss": function() { this.do_action(this.next_action, {clear_breadcrumbs: true}); },
    },

    init: function(parent, action) {
        var self = this;
        this._super.apply(this, arguments);
        this.activeBarcode = true;

        // if no correct action given (due to an erroneous back or refresh from the browser), we set the dismiss button to return
        // to the (likely) appropriate menu, according to the user access rights
        if(!action.attendance) {
            this.activeBarcode = false;
            this.getSession().user_has_group('hr_attendance.group_hr_attendance_user').then(function(has_group) {
                if(has_group) {
                    self.next_action = 'hr_attendance.hr_attendance_action_kiosk_mode';
                } else {
                    self.next_action = 'hr_attendance.hr_attendance_action_my_attendances';
                }
            });
            return;
        }

        this.next_action = action.next_action || 'hr_attendance.hr_attendance_action_my_attendances';
        // no listening to barcode scans if we aren't coming from the kiosk mode (and thus not going back to it with next_action)
        if (this.next_action != 'hr_attendance.hr_attendance_action_kiosk_mode' && this.next_action.tag != 'hr_attendance_kiosk_mode') {
            this.activeBarcode = false;
        }

        this.attendance = action.attendance;
        // We receive the check in/out times in UTC
        // This widget only deals with display, which should be in browser's TimeZone
        this.attendance.check_in = this.attendance.check_in && moment.utc(this.attendance.check_in).local();
        this.attendance.check_out = this.attendance.check_out && moment.utc(this.attendance.check_out).local();
        this.previous_attendance_change_date = action.previous_attendance_change_date && moment.utc(action.previous_attendance_change_date).local();

        // check in/out times displayed in the greeting message template.
        this.format_time = time.getLangTimeFormat();
        this.attendance.check_in_time = this.attendance.check_in && this.attendance.check_in.format(this.format_time);
        this.attendance.check_out_time = this.attendance.check_out && this.attendance.check_out.format(this.format_time);

        // extra hours amount displayed in the greeting message template.
        this.total_overtime_float = action.total_overtime; // Used for comparison in template
        this.total_overtime = field_utils.format.float_time(this.total_overtime_float)

        if (action.hours_today) {
            var duration = moment.duration(action.hours_today, "hours");
            this.hours_today = duration.hours() + ' hours, ' + duration.minutes() + ' minutes';
        }

        this.employee_name = action.employee_name;
        this.attendanceBarcode = action.barcode;
    },

    start: function() {
        if (this.attendance) {
            this.attendance.check_out ? this.farewell_message() : this.welcome_message();
        }
        if (this.activeBarcode) {
            core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        }
        return this._super.apply(this, arguments);
    },

    welcome_message: function() {
        var self = this;
        var now = this.attendance.check_in.clone();
        this.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);

        if (now.hours() < 5) {
            this.$('.o_hr_attendance_message_message').append(_t("Good night"));
        } else if (now.hours() < 12) {
            if (now.hours() < 8 && Math.random() < 0.3) {
                if (Math.random() < 0.75) {
                    this.$('.o_hr_attendance_message_message').append(_t("The early bird catches the worm"));
                } else {
                    this.$('.o_hr_attendance_message_message').append(_t("First come, first served"));
                }
            } else {
                this.$('.o_hr_attendance_message_message').append(_t("Good morning"));
            }
        } else if (now.hours() < 17){
            this.$('.o_hr_attendance_message_message').append(_t("Good afternoon"));
        } else if (now.hours() < 23){
            this.$('.o_hr_attendance_message_message').append(_t("Good evening"));
        } else {
            this.$('.o_hr_attendance_message_message').append(_t("Good night"));
        }
        if(this.previous_attendance_change_date){
            var last_check_out_date = this.previous_attendance_change_date.clone();
            if(now - last_check_out_date > 24*7*60*60*1000){
                this.$('.o_hr_attendance_random_message').html(_t("Glad to have you back, it's been a while!"));
            } else {
                if(Math.random() < 0.02){
                    this.$('.o_hr_attendance_random_message').html(_t("If a job is worth doing, it is worth doing well!"));
                }
            }
        }
    },

    farewell_message: function() {
        var self = this;
        var now = this.attendance.check_out.clone();
        this.return_to_main_menu = setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);

        if(this.previous_attendance_change_date){
            var last_check_in_date = this.previous_attendance_change_date.clone();
            if(now - last_check_in_date > 1000*60*60*12){
                this.$('.o_hr_attendance_warning_message').show().append(_t("<b>Warning! Last check in was over 12 hours ago.</b><br/>If this isn't right, please contact Human Resource staff"));
                clearTimeout(this.return_to_main_menu);
                this.activeBarcode = false;
            } else if(now - last_check_in_date > 1000*60*60*8){
                this.$('.o_hr_attendance_random_message').html(_t("Another good day's work! See you soon!"));
            }
        }

        if (now.hours() < 12) {
            this.$('.o_hr_attendance_message_message').append(_t("Have a good day!"));
        } else if (now.hours() < 14) {
            this.$('.o_hr_attendance_message_message').append(_t("Have a nice lunch!"));
            if (Math.random() < 0.05) {
                this.$('.o_hr_attendance_random_message').html(_t("Eat breakfast as a king, lunch as a merchant and supper as a beggar"));
            } else if (Math.random() < 0.06) {
                this.$('.o_hr_attendance_random_message').html(_t("An apple a day keeps the doctor away"));
            }
        } else if (now.hours() < 17) {
            this.$('.o_hr_attendance_message_message').append(_t("Have a good afternoon"));
        } else {
            if (now.hours() < 18 && Math.random() < 0.2) {
                this.$('.o_hr_attendance_message_message').append(_t("Early to bed and early to rise, makes a man healthy, wealthy and wise"));
            } else {
                this.$('.o_hr_attendance_message_message').append(_t("Have a good evening"));
            }
        }
    },

    _onBarcodeScanned: function(barcode) {
        var self = this;
        if (this.attendanceBarcode !== barcode){
            if (this.return_to_main_menu) {  // in case of multiple scans in the greeting message view, delete the timer, a new one will be created.
                clearTimeout(this.return_to_main_menu);
            }
            core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
            this._rpc({
                    model: 'hr.employee',
                    method: 'attendance_scan',
                    args: [barcode, ],
                })
                .then(function (result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.displayNotification({ title: result.warning, type: 'danger' });
                        setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);
                    }
                }, function () {
                    setTimeout( function() { self.do_action(self.next_action, {clear_breadcrumbs: true}); }, 5000);
                });
        }
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearTimeout(this.return_to_main_menu);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('hr_attendance_greeting_message', GreetingMessage);

return GreetingMessage;

});
