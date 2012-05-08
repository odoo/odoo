openerp.hr_attendance = function(instance) {
    var QWeb = instance.web.qweb;
    instance.hr_attendance.AttendanceNotifier = instance.web.Widget.extend({
        template: 'AttendanceNotifier',
        init: function(parent){
              this._super(parent);
              this.session = parent.session;
              this.employee = new instance.web.DataSetSearch(this, 'hr.employee', this.session.user_context, [['user_id','=', this.session.uid]]);
        },
        renderElement: function() {
            var self = this;
            if (this.attendance_status == 'present'){
                action_type = 'sign_out';
            }
            else{
                action_type = 'sign_in';
            }
            this.$element = $(QWeb.render(this.template, {'action':action_type}));
            element = $('.oe_attendance_button')
            if (element.length != 0){
                element.attr('src', this.$element.attr('src'));
            }
            else{
                this.$element.appendTo($('.oe_systray'));
                this.$element.click(self.on_click);
            }
        },

        on_click: function() {
            var self = this;
            action = new instance.web.DataSetSearch(this, 'ir.actions.act_window', {}, [['res_model', '=', 'hr.sign.in.out']]);
            action.read_slice().done(function(action) {
                action = action[0];
                action.context = JSON.parse(action.context);
                var action_manager = new instance.web.ActionManager(self);
                action_manager.do_action(action, function(){
                    self.employee.read_slice(['state']).done(function(employee) {
                        if(_.isEmpty(employee)) return;
                        self.attendance_status = employee[0]['state'];
                        self.renderElement();
                    });
                });
            });
        },
    });

    
    instance.web.UserMenu.include({
        do_update: function() {
            var self = this;
            this._super();
            this.update_promise.then(function() {
                attendance = new instance.hr_attendance.AttendanceNotifier(self);
                attendance.employee.read_slice(['state']).done(function(employee) {
                    if(_.isEmpty(employee)) return;
                    attendance.attendance_status = employee[0]['state'];
                    attendance.renderElement();
                });
            });
        },
    });
}
