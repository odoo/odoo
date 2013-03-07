openerp.portal_anonymous = function(instance) {

    instance.web.Session.include({
        load_translations: function() {
            var self = this;
            // browser_lang can contain 'xx' or 'xx_XX'
            // we use the 'xx' to find matching languages installed in the DB
            var browser_lang = (navigator.language || navigator.userLanguage).replace('-', '_');
            // By default for anonymous session.user_context.lang === 'en_US',
            // so do nothing if browser_lang is contained in 'en_US' (like 'en' or 'en_US')
            if (this.username === 'anonymous' && this.user_context.lang.indexOf(browser_lang) === -1) {
                return (new instance.web.Model('res.lang')).query(['code', 'iso_code'])
                    .filter([['code', 'like', browser_lang.substring(0, 2).toLowerCase()]]).all()
                .then(function(langs) {
                    // If langs is empty (OpenERP doesn't support the language),
                    // then don't change session.user_context.lang
                    if (langs.length > 0) {
                        // Try to get the right user preference in the browser, else
                        // get the shortest language returned ('xx' country code) or
                        // just the first one
                        var l = _.filter(langs, function(lang) { return lang.code === browser_lang || lang.iso_code === browser_lang; });
                        if (!_.isEmpty(l)) {
                            self.user_context.lang = l[0].code;
                        } else {
                            l = _.filter(langs, function(lang) {
                                return lang.iso_code === _.pluck(langs, 'iso_code')
                                    .sort(function(a, b) {
                                        return a.length - b.length;
                                    })[0];
                            });
                            self.user_context.lang = l[0].code;
                        }
                    }
                    return self.rpc('/web/webclient/translations', { mods: self.module_list, lang: self.user_context.lang }).done(function(trans) {
                        instance.web._t.database.set_bundle(trans);
                    });
                });
            }
            return this._super();
        },
    });

    instance.web.Login.include({
        start: function() {
            var self = this;
            return $.when(this._super()).then(function() {
                if (!self.session.session_is_valid() && !(self.params.token || self.params.login)) {
                    self.remember_credentials = false;
                    // XXX get login/pass from server (via a rpc call) ?
                    return self.do_login(self.selected_db, 'anonymous', 'anonymous');
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
                p.$el.find('.oe_leftbar, .oe_topbar').hide();
                self.session.session_logout().done(function () {
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
    });

};
