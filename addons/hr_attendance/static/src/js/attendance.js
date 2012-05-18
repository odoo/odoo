openerp.hr_attendance = function(instance) {
   /** var QWeb = instance.web.qweb;
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
	        var el = $("div.presence_slider");
            el.click(function(){
                    if(self.employee.state == 'present'){                        
                        el.animate({"left": "48px"}, "slow");                        
                        self.on_click();
                    }else{                        
                        el.animate({"left": "-8px"}, "slow");
                        
                    }
             });
        },
        do_update_notifier: function(){
            var self = this;
            var el = $('img.oe_topbar_avatar');


            

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
               //window.location.reload();
                self.renderElement()
            });
        },
    });
    /* instance.web.DataSet.include({
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
        callback: function()
        {
            this.__super();
            
                .....
        }

    }); */

    instance.web.UserMenu.include({
        do_update_attendance: function() {
            var self = this;
            console.log("click.........",self);
            hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [[self.employee.id]]).done(function(result){
                if (!result) return;
                if(self.employee.state == 'present')
                    self.employee.state = 'absent';
                else
                    self.employee.state = 'present';
                self.do_slide(self.employee.state);                
            });
        },
        do_slide:function(attendance_state)
        {
            if(attendance_state == 'present')
                this.oe_attendance_slider.animate({"left": "48px"}, "slow");                                               
            else                        
                this.oe_attendance_slider.animate({"left": "-8px"}, "slow");
        },
        check_attendance: function(){
            var self = this;
            var employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [['user_id','=', self.session.uid]]);
            return employee.read_slice(['id','name','state']).pipe(function(res) {
                if(_.isEmpty(res)) return;
                self.employee = res[0];
                self.do_slide(self.employee.state);
            });
        },
        do_update: function () {
            this._super();
            var self = this;
            var fct = function() {
                self.oe_attendance_slider = self.$element.find('.oe_attendance_slider');
                self.oe_attendance_slider.click(self.do_update_attendance);
                return self.check_attendance();
                
            };
            this.update_promise = this.update_promise.pipe(fct, fct);
        },
    });
}
