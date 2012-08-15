openerp.auth_oauth = function(instance) {
    var QWeb = instance.web.qweb;

    instance.web.Login = instance.web.Login.extend({
        start: function(parent, params) {
            var d = this._super.apply(this, arguments);
            this.$element.on('click', 'a.oe_oauth_sign_in', this.on_oauth_sign_in);
            this.oauth_providers = [];
            if(this.params.oauth_error === 1) {
                this.do_warn("Sign up error.","Sign up is not allowed on this database.");
            } else if(this.params.oauth_error === 2) {
                this.do_warn("Authentication error","");
            }
            return d.then(this.do_oauth_load);
        },
        do_oauth_load: function() {
            var db = this.$("form [name=db]").val();
            if (db) {
                this.rpc("/auth_oauth/list_providers", { dbname: db }).then(this.on_oauth_loaded);
            }
        },
        on_oauth_loaded: function(result) {
            this.oauth_providers = result;
            console.log(result);
            var buttons = QWeb.render("auth_oauth.Login.button",{"widget":this});
            console.log(buttons);
            this.$(".oe_login_pane form ul").after(buttons);
        },
        oauth_url: function(state) {
        },
        on_oauth_sign_in: function(ev) {
            ev.preventDefault();
            var index = $(ev.target).data('index');
            var p = this.oauth_providers[index];
            var ret = location.protocol+"//"+location.host+"/";
            var dbname = self.$("form [name=db]").val();
            var params = {
                response_type: 'token',
                client_id: p.client_id,
                redirect_uri: ret,
                scope: p.scope,
                state: dbname,
            };
            var url = p.auth_endpoint + '?' + $.param(params);
            window.location = url;
        },
    });

    instance.web.WebClient = instance.web.WebClient.extend({
        start: function() {
            this._super.apply(this, arguments);
            var params = $.deparam(window.location.hash.substring(1));
            // alert(JSON.stringify(params));
            if (params.hasOwnProperty('access_token')) {
                var url = "/auth_oauth/signin" + '?' + $.param(params);
                window.location = url;
            }
        },
    });

};
