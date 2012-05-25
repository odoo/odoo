openerp.hr_attendance = function(instance) {
    var QWeb = instance.web.qweb;
    _t = instance.web._t;
    
    instance.web.currentform = false;
    instance.web.currentlist = false;
    instance.web.attendanceslider = false;
    
    instance.hr_attendance.AttendanceSlider = instance.web.Widget.extend({
        template: 'AttendanceSlider',
        init: function(parent){
            this.titles = {'present' :_t("Present"),
                             'absent' :_t("Absent")          
                            }
            this._super(parent);
            this.session = parent.session;
            this.parent_element = parent.$element ;            
        },
        renderElement: function(){
            this.$element = $(QWeb.render(this.template,this.titles));            
            this.parent_element.prepend(this.$element);
            this.$oe_attendance_slider = this.$element.find(".oe_attendance_slider");
            this.$oe_attendance_slider.click(this.do_update_attendance);
        },
        do_update_attendance: function() {
            var self = this;
            if(!self.employee)return;
            hr_employee = new instance.web.DataSet(self, 'hr.employee');
            hr_employee.call('attendance_action_change', [[self.employee.id]]).done(function(result){
                if (!result) return;
                if(self.employee.state == 'present')
                    self.employee.state = 'absent';
                else
                    self.employee.state = 'present';
                self.do_slide(self.employee.state);
                if(instance.web.currentlist){
                    instance.web.currentlist.reload();
                }
                if(instance.web.currentform){
                    //tofix: it should be in hr_timesheet_sheet module
                    if (instance.web.currentform.model == 'hr_timesheet_sheet.sheet'){
                        model = new instance.web.DataSet(self, instance.web.currentform.model);
                        model.call('date_today', [instance.web.currentform.dataset.ids]).done(function(result){instance.web.currentform.reload();});
                    }
                    else{
                        instance.web.currentform.reload();
                    }
                    
                }
            });
        },
        do_slide:function(attendance_state)
        {
            if(attendance_state == 'present'){
                this.$oe_attendance_slider.attr("title",_t("Sign Out"));
                this.$oe_attendance_slider.animate({"left": "48px"}, "slow");}
            else{
                this.$oe_attendance_slider.attr("title",_t("Sign In"));
                this.$oe_attendance_slider.animate({"left": "-8px"}, "slow");}

        },
        check_attendance: function(){
            var self = this;
            self.employee = false;
            this.$element.find(".oe_attendance_status").hide();
            var employee = new instance.web.DataSetSearch(self, 'hr.employee', self.session.user_context, [['user_id','=', self.session.uid]]);
            return employee.read_slice(['id','name','state']).pipe(function(res) {
                if(_.isEmpty(res)) return;
                self.$element.find(".oe_attendance_status").show();
                self.employee = res[0];
                self.do_slide(self.employee.state);
            });
        },
    });
    
    instance.web.ListView.include({
        init:function(parent, dataset, view_id, options)
        {
            this._super(parent, dataset, view_id, options);
            if (this.model == 'hr.employee' || this.model == 'hr.attendance' || this.model == 'hr_timesheet_sheet.sheet')
                instance.web.currentlist = this;
        }
    });
    
    
    instance.web.FormView.include({
        init: function(parent, dataset, view_id, options) {
            this._super(parent, dataset, view_id, options);
            if (this.model == 'hr.employee' || this.model == 'hr.attendance' || this.model == 'hr_timesheet_sheet.sheet')
                instance.web.currentform = this;
        },
        reload: function(){
            var re = this._super();
            if (!instance.web.attendanceslider) return re;
            if (this.model == 'hr.employee' || this.model == 'hr.attendance' || this.model == 'hr_timesheet_sheet.sheet')
                instance.web.attendanceslider.check_attendance();            
            return re;            
        },                
    }),
    
    instance.web.UserMenu.include({
        do_update: function () {
            this._super();
            var self = this;
            var fct = function() {                
                instance.web.attendanceslider = new instance.hr_attendance.AttendanceSlider(self);
                instance.web.attendanceslider.renderElement();
                return instance.web.attendanceslider.check_attendance();                
            };
            this.update_promise = this.update_promise.pipe(fct, fct);
        },
    });
}
