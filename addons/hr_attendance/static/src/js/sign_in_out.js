openerp.hr_attendance = function(openerp) {
    
    openerp.hr_attendance.SignIn = openerp.web.Widget.extend({
        template: 'SignInNotifier',
        start: function() {
            this.$element.on('click', '.sign_in', this.getParent().on_sign_in_out);
        }
    });
    
    openerp.hr_attendance.SignOut = openerp.web.Widget.extend({
        template: 'SignOutNotifier',
        
        start: function() {
            this.$element.on('click', '.sign_out', this.getParent().on_sign_in_out);
        }
    });
    
    openerp.hr_attendance.SignInOut = openerp.web.Widget.extend({
        template: "SignInOutNotifier",
        init: function() {
            this._super.apply(this, arguments);
            this.dataset = new openerp.web.DataSetSearch(
                this,
                'hr.employee',
                this.session.user_context,
                [['user_id','=', this.session.uid]]);
        },
        
        start: function() {
            return this.dataset.read_slice(['state']).done(this.do_sign_in_out);
        },
        
        do_sign_in_out: function(user) {
            if(_.isEmpty(user)) return;
            if(user[0]['state'] === 'present') {
                this.sign_out = new openerp.hr_attendance.SignOut(this);
                this.sign_out.appendTo(this.$element);
            } else {
                this.sign_in = new openerp.hr_attendance.SignIn(this);
                this.sign_in.appendTo(this.$element);
            }
        },
        
        on_sign_in_out: function(evt) {
            var self = this;
            new openerp.web.DataSetSearch(
                this, 
                'ir.actions.act_window',
                {},
                [['res_model', '=', 'hr.sign.in.out']])
            .read_slice().done(function(action) {
                action = action[0];
                action.context = JSON.parse(action.context);
                var action_manager = new openerp.web.ActionManager(self);
                action_manager.do_action(action, function() {
                    self.on_close($(evt.currentTarget).attr('class'));
                });
            });
        },
        
        on_close: function(target) {
            if(target === 'sign_in') {
                this.sign_in.destroy();
                this.sign_out = new openerp.hr_attendance.SignOut(this);
                this.sign_out.appendTo(this.$element);
            } else if(target === 'sign_out') {
                this.sign_out.destroy();
                this.sign_in = new openerp.hr_attendance.SignIn(this);
                this.sign_in.appendTo(this.$element);
            }
        }
    });
    
    openerp.web.UserMenu.include({
        do_update: function() {
            var self = this;
            this._super();
            this.update_promise.then(function() {
                self.hr_sign_in_out = new openerp.hr_attendance.SignInOut(self);
                self.hr_sign_in_out.appendTo(openerp.webclient.$element.find('.oe_systray'))
            });
        }
    });
}
