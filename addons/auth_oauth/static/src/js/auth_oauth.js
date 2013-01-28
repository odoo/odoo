openerp.auth_oauth = function(instance) {
    var QWeb = instance.web.qweb;

    instance.web.Login.include({
        start: function(parent, params) {
            var self = this;
            var d = this._super.apply(this, arguments);
            this.$el.on('click', 'a.zocial', this.on_oauth_sign_in);
            this.oauth_providers = [];
            if(this.params.oauth_error === 1) {
                this.do_warn("Sign up error.","Sign up is not allowed on this database.");
            } else if(this.params.oauth_error === 2) {
                this.do_warn("Authentication error","");
            }
            return d.done(this.do_oauth_load).fail(function() {
                self.do_oauth_load([]);
            });
        },
        on_db_loaded: function(result) {
            this._super.apply(this, arguments);
            this.$("form [name=db]").change(this.do_oauth_load);
        },
        do_oauth_load: function() {
            var db = this.$("form [name=db]").val();
            if (db) {
                this.rpc("/auth_oauth/list_providers", { dbname: db }).done(this.on_oauth_loaded);
            }
        },
        on_oauth_loaded: function(result) {
            this.oauth_providers = result;
            var params = $.deparam($.param.querystring());
            if (this.oauth_providers.length === 1 && params.type === 'signup') {
                this.do_oauth_sign_in(this.oauth_providers[0]);
            } else {
                this.$('.oe_oauth_provider_login_button').remove();
                var buttons = QWeb.render("auth_oauth.Login.button",{"widget":this});
                this.$(".oe_login_pane form ul").after(buttons);
            }
        },
        on_oauth_sign_in: function(ev) {
            ev.preventDefault();
            var index = $(ev.target).data('index');
            var provider = this.oauth_providers[index];
            return this.do_oauth_sign_in(provider);
        },
        do_oauth_sign_in: function(provider) {
            var return_url = _.str.sprintf('%s//%s/auth_oauth/signin', location.protocol, location.host);
            if (instance.session.debug) {
                return_url += '?debug';
            }
            var state = this._oauth_state(provider);
            var params = {
                response_type: 'token',
                client_id: provider.client_id,
                redirect_uri: return_url,
                scope: provider.scope,
                state: JSON.stringify(state),
            };
            var url = provider.auth_endpoint + '?' + $.param(params);
            window.location = url;
        },
        _oauth_state: function(provider) {
            // return the state object sent back with the redirected uri
            var dbname = this.$("form [name=db]").val();
            return {
                d: dbname,
                p: provider.id,
            };
        },
    });

};
