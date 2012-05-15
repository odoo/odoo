openerp.hr_attendance = function(instance) {
    var QWeb = instance.web.qweb;
    instance.hr_attendance.attendancestatus = false,
    instance.hr_attendance.checkstatus = function(){
        attendance = instance.hr_attendance.currentstatus;
        if (!attendance){
        	attendance = new instance.hr_attendance.AttendanceNotifier(self);
            instance.hr_attendance.currentstatus = attendance;
        }
        attendance.renderElement();
    },
    instance.hr_attendance.callback = function(callback){
        var old_callback = callback;
	    callback = function(result){
			    if(old_callback){old_callback(result);}
			    instance.hr_attendance.checkstatus();
	    }
        return callback;
    },
    instance.hr_attendance.AttendanceNotifier = instance.web.Widget.extend({
        template: 'AttendanceNotifier',
        renderElement: function() {
            var self = this;
            employee = new instance.web.DataSetSearch(this, 'hr.employee', this.session.user_context, [['user_id','=', this.session.uid]]);
	        employee.read_slice(['id','name','state']).done(function(employee) {
	            if(_.isEmpty(employee)) return;
                self.employee = employee[0];
	            self.do_update_notifier();
	        });
        },
        do_update_notifier: function(){
            var self = this;
            this.$element = $(QWeb.render(this.template, {'employee':this.employee}));
            this.$element.click(self.on_click);
            element = $('.oe_attendance_button')
            if (element.length != 0){
                element.replaceWith(this.$element);
            }
            else{
                this.$element.appendTo($('.oe_systray'));

            }
        },

        on_click: function() {
            var self = this;
            hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [[self.employee.id]]).done(function(result){
                window.location.reload();
                //self.renderElement()
            });
        },
    });
    instance.web.DataSet.include({
        create: function(data, callback, error_callback) {
            if (this._model.name == "hr.attendance"){
    			callback = instance.hr_attendance.callback(callback);
    		}
            return this._super(data, callback, error_callback);
        },
        write: function (id, data, options, callback, error_callback) {
            if (this._model.name == "hr.attendance"){
    			callback = instance.hr_attendance.callback(callback);
    		}
            return this._super(id, data, options, callback, error_callback);
        },
  	    unlink: function(ids, callback, error_callback) {
            if (this._model.name == "hr.attendance"){
    			callback = instance.hr_attendance.callback(callback);
    		}
            return this._super(ids, callback, error_callback);
        },
        call_button: function (method, args, callback, error_callback) {
            if (method == "attendance_action_change"){
    			callback = instance.hr_attendance.callback(callback);
    		}
            return this._super(method, args, callback, error_callback);
        },

    });

    instance.web.UserMenu.include({
        do_update: function() {
            var self = this;
            this._super();
            this.update_promise.then(function() {
                instance.hr_attendance.checkstatus();
            });
        },
    });
}
