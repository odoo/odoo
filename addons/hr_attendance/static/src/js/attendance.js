
openerp.hr_attendance = function (instance) {
    
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_attendance.AttendanceSlider = instance.web.Widget.extend({
        template: 'AttendanceSlider',
        init: function (parent) {
            this._super(parent);
        },
        start: function() {
            var self = this;
            this.on("change:signed_in", this, function() {
                this.$el.toggleClass("oe_attendance_nosigned", ! this.get("signed_in"));
                this.$el.toggleClass("oe_attendance_signed", this.get("signed_in"));
            });
            this.$(".oe_attendance_signin").click(function() {
                self.do_update_attendance();
            });
            this.$(".oe_attendance_signout").click(function() {
                self.do_update_attendance();
            });
            return this.check_attendance();
        },
        do_update_attendance: function () {
            var self = this;
            var hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [
                [self.employee.id]
            ]).done(function (result) {
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
            return employee.read_slice(['id', 'name', 'state']).pipe(function (res) {
                if (_.isEmpty(res))
                    return;
                self.$el.show();
                self.employee = res[0];
                self.set({"signed_in": self.employee.state !== "absent"});
            });
        },
    });

    instance.web.UserMenu.include({
        do_update: function () {
            this._super();
            var self = this;
            this.update_promise = this.update_promise.then(function () {
                if (self.attendanceslider)
                    return;
                self.attendanceslider = new instance.hr_attendance.AttendanceSlider(self);

                self.attendanceslider.prependTo(instance.webclient.$('.oe_systray'));
            });
        },
    });
}
