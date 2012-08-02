openerp.anonymous = function(instance) {

    instance.web.Login.include({
        start: function() {
            var self = this;
            return $.when(this._super()).pipe(function() {
                var dblist = self._db_list || [];
                if (!self.session.session_is_valid() && dblist.length === 1) {
                    self.remember_credentials = false;
                    // XXX get login/pass from server (via a rpc call) ?
                    return self.do_login(dblist[0], 'anonymous', 'anonymous')
                }

            });
        },
    });

    instance.web.UserMenu.include({
        init: function(parent) {
            this._super(parent);
            if (this.session.username == 'anonymous') {
                this.template = 'UserMenu.anonymous';
                this.do_update = function() {};     // avoid change of avatar
            }
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$element.find('.oe_topbar_anonymous_login').click(function() {
                var p = self.getParent();
                var am = p.action_manager;
                p.$element.find('.oe_leftbar').hide();
                am.do_action({
                    type:'ir.actions.client',
                    tag:'login',
                    target: 'new',
                    params: {
                        login_successful: function() {
                            am.do_action("reload");
                        }
                    }
                });
            });
        }
    });

};
