openerp.signup = function(instance) {

    instance.web.UserMenu.include({
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$element.find('a.oe_topbar_signup').click(function() {
                var p = self.getParent();
                var am = p.action_manager;
                am.do_action({
                    type:'ir.actions.act_window',
                    res_model: 'signup.signup',
                    views: [[false, 'form']],
                    target: 'new',
                    name: 'Sign Up'
                });
            });
        }
    });

};
