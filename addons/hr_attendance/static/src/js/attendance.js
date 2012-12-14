
openerp.hr_attendance = function (instance) {
    
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;

    instance.hr_attendance.AttendanceSlider = instance.web.Widget.extend({
        template: 'AttendanceSlider',
        init: function (parent) {
            this._super(parent);
            this.set({"signed_in": false});
        },
        start: function() {
            var self = this;
            var tmp = function() {
                this.$el.toggleClass("oe_attendance_nosigned", ! this.get("signed_in"));
                this.$el.toggleClass("oe_attendance_signed", this.get("signed_in"));
            };
            this.on("change:signed_in", this, tmp);
            _.bind(tmp, this)();
            this.$(".oe_attendance_signin").click(function() {
                self.do_update_attendance();
            });
            this.$(".oe_attendance_signout").click(function() {
                self.do_update_attendance();
            });
            this.$el.tipsy({
                title: function() {
                    var last_text = instance.web.format_value(self.last_sign, {type: "datetime"});
                    var current_text = instance.web.format_value(new Date(), {type: "datetime"});
                    var duration = self.last_sign ? $.timeago(self.last_sign) : "none";
                    if (self.get("signed_in")) {
                        return _.str.sprintf(_t("Last sign in: %s,<br />%s.<br />Click to sign out."), last_text, duration);
                    } else {
                        return _.str.sprintf(_t("Click to Sign In at %s."), current_text);
                    }
                },
                html: true,
            });
            return this.check_attendance();
        },
        do_update_attendance: function () {
            var self = this;
            var hr_employee = new instance.web.DataSet(self, 'hr.employee');
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
            var employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [
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
                self.last_sign = instance.web.str_to_datetime(self.employee.last_sign);
                self.set({"signed_in": self.employee.state !== "absent"});
            });
        },
    });

    instance.web.UserMenu.include({
        do_update: function () {
            this._super();
            var self = this;
            this.update_promise.done(function () {
                if (!_.isUndefined(self.attendanceslider)) {
                    return;
                }
                // check current user is an employee
                var Users = new instance.web.Model('res.users');
                Users.call('has_group', ['base.group_user']).done(function(is_employee) {
                    if (is_employee) {
                        self.attendanceslider = new instance.hr_attendance.AttendanceSlider(self);
                        self.attendanceslider.prependTo(instance.webclient.$('.oe_systray'));
                    } else {
                        self.attendanceslider = null;
                    }
                });
            });
        },
    });
};
