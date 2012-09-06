
openerp.hr_attendance = function (instance) {
    
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_attendance.AttendanceSlider = instance.web.Widget.extend({
        template: 'AttendanceSlider',
        init: function (parent) {
            this.titles = {
                'present': _t("Present"),
                'absent': _t("Absent")
            }
            this._super(parent);
            this.session = parent.session;
            this.parent_element = parent.$el;
        },
        start: function () {
            this.$oe_attendance_slider = this.$el.find(".oe_attendance_slider");
            this.$oe_attendance_slider.click(this.do_update_attendance);
        },
        do_update_attendance: function () {
            var self = this;
            if (!self.employee) return;
            hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [
                [self.employee.id]
            ]).done(function (result) {
                if (!result) return;
                if (self.employee.state == 'present') self.employee.state = 'absent';
                else self.employee.state = 'present';
                self.do_slide(self.employee.state);
            });
        },
        do_slide: function (attendance_state) {
            if (attendance_state == 'present') {
                this.$oe_attendance_slider.attr("title", _t("Sign Out"));
                this.$oe_attendance_slider.animate({
                    "left": "48px"
                }, "slow");
            } else {
                this.$oe_attendance_slider.attr("title", _t("Sign In"));
                this.$oe_attendance_slider.animate({
                    "left": "-8px"
                }, "slow");
            }

        },
        check_attendance: function () {
            var self = this;
            self.employee = false;
            this.$el.find(".oe_attendance_status").hide();
            var employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [
                ['user_id', '=', self.session.uid]
            ]);
            return employee.read_slice(['id', 'name', 'state']).pipe(function (res) {
                if (_.isEmpty(res)) return;
                self.$el.find(".oe_attendance_status").show();
                self.employee = res[0];
                self.do_slide(self.employee.state);
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
                self.attendanceslider.check_attendance();
            });
        },
    });
}
