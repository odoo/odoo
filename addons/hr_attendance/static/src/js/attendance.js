openerp.hr_attendance = function(instance) {	
    var QWeb = instance.web.qweb;
    instance.hr_attendance.AttendanceNotifier = instance.web.Widget.extend({
        template: 'AttendanceNotifier',
        
        init: function(attendance_status){
          console.log('nnnnnn',this)
          this.attendance_status = attendance_status;
        },
        renderElement: function() {
            console.log('render',this)
            if (this.attendance_status == 'present'){
                action_type = 'sign_out';
            }
            else{
                action_type = 'sign_in';
            }
            this.$element = $(QWeb.render(this.template, {'action':action_type}));
            console.log('element',this.$element)
            this.$element.click(this.on_attendance);
        },
        
        
        
        on_attendance: function(event) {
            var self = this;
            console.log('eventtt',event)
            action = new instance.web.DataSetSearch(this, 'ir.actions.act_window', {}, [['res_model', '=', 'hr.sign.in.out']]);
            action.read_slice().done(function(action) {
                action = action[0];
                action.context = JSON.parse(action.context);
                var action_manager = new instance.web.ActionManager(self);
                action_manager.do_action(action, function(){
                    window.location.reload();                   
                });
            });
        },
    });
    
    
    instance.web.UserMenu.include({
        do_update: function() {
            var self = this;
            this._super();
            this.update_promise.then(function() {
                self.employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [['user_id','=', self.session.uid]]);
                self.employee.read_slice(['state']).done(self.do_update_attendance_status);
            });
        },
        do_update_attendance_status: function(employee) {
            if(_.isEmpty(employee)) return;
            attendance_status = employee[0]['state']
            self.attendance = new instance.hr_attendance.AttendanceNotifier(attendance_status);
            self.attendance.appendTo(instance.webclient.$element.find('.oe_systray'))
        },
    });
}
