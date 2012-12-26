openerp.portal_anonymous = function(instance) {

    instance.web.Session.include({
        load_translations: function() {
            if (this.username === 'anonymous') {
                var l = (navigator.language) ? navigator.language : navigator.userLanguage;
                var params = { mods: this.module_list, lang: l };
                return this.rpc('/web/webclient/translations', params).done(function(trans) {
                    console.log(trans);
                    instance.web._t.database.set_bundle(trans);
                });
            }
            return this._super();
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
