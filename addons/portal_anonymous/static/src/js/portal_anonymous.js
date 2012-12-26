openerp.portal_anonymous = function(instance) {

    instance.web.Session.include({
        load_translations: function() {
            var self = this;
            if (self.username === 'anonymous') {
                var browser_lang = (navigator.language || navigator.userLanguage).replace('-', '_');
                if (browser_lang.length === 2) {
                    return (new instance.web.Model('res.lang')).query(['code'])
                        .filter([['iso_code', '=', browser_lang]]).all()
                        .then(function(result) {
                            self.user_context.lang = result[0].code;
                        });
                }
                self.user_context.lang = browser_lang;
            }
            return self._super();
        },
    });

    instance.web.Login.include({
        start: function() {
            var self = this;
            return $.when(this._super()).then(function() {
                var params = $.deparam($.param.querystring());
                var dblist = self.db_list || [];
                if (!self.session.session_is_valid() && dblist.length === 1 && (!params.token || !params.login)) {
                    self.remember_credentials = false;
                    // XXX get login/pass from server (via a rpc call) ?
                    return self.do_login(dblist[0], 'anonymous', 'anonymous');
                }
            });
        },
    });

    instance.web.UserMenu.include({
        init: function(parent) {
            this._super(parent);
            if (this.session.username == 'anonymous') {
                this.template = 'UserMenu.portal_anonymous';
                this.do_update = function() {};     // avoid change of avatar
            }
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.$el.find('a.login').click(function() {
                var p = self.getParent();
                var am = p.action_manager;
                p.$el.find('.oe_leftbar').hide();
                am.do_action({
                    type:'ir.actions.client',
                    tag:'login',
                    target: 'current',
                    params: {
                        login_successful: function() {
                            am.do_action("reload");
                        }
                    }
                });
            });
        }
    });

    instance.web.WebClient.include({
        check_timezone: function() {
            if (this.session.username !== 'anonymous') {
                return this._super.apply(this, arguments);
            }
            return false;
        },
        // Avoid browser preloading
        show_application: function() {
            var params = $.deparam($.param.querystring());
            if (!!params.token || !!params.login) {
                return this.show_login();
            }
            return this._super();
        },
    });

};
