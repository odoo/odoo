openerp.anonymous = function(instance) {

    instance.web.client_actions.add("login", "instance.web.Login");

    instance.web.WebClient.include({
        show_login: function() {
            var self = this, _super = this._super;
            this.login.load_db_list().then(function() {
                var dblist = self.login._db_list;
                if (dblist && dblist.length === 1) {
                    self.login.remember_credentials = false;
                    // XXX get login/pass from server (via a rpc call) ?
                    self.login.do_login(dblist[0], 'anonymous', 'anonymous').fail(function() {
                        _super.apply(self, []);
                    });
                } else {
                    _super.apply(self, []);
                }
            });
        },
        restart: function() {
            return this.start();
        }
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
                am.do_action({type:'ir.actions.client', tag:'login'});
                am.client_widget.on('login', p, p.restart);
            });
        }
    });

};
