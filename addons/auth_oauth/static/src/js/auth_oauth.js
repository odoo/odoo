openerp.auth_oauth = function(instance) {
    var QWeb = instance.web.qweb;

    instance.web.Login = instance.web.Login.extend({
        start: function(parent, params) {
            this._super.apply(this, arguments);
            var self = this;
            self.$element.on('click', '.oe_login_oauth a', this.on_google_oauth);
        },
        oauth_url: function(state) {
            var endpoint = 'https://accounts.google.com/o/oauth2/auth';
            var params = {
                response_type: 'token',
                client_id: '108010644258-duuhmp6pu7li4tsmnqg7j9rvdeklg0ki.apps.googleusercontent.com',
                redirect_uri: 'https://localhost/',
                scope: 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
                state: state,
            };
            var url = endpoint + '?' + $.param(params);
            return url;
        },
        on_google_oauth: function(ev) {
            var dbname = self.$("form [name=db]").val();
            var url = this.oauth_url(dbname);
            window.location = url;
        },
    });

    instance.web.WebClient = instance.web.WebClient.extend({
        start: function() {
            this._super.apply(this, arguments);
            var params = $.deparam(window.location.hash.substring(1));
            if (params.hasOwnProperty('access_token')) {
                var url = "/auth_oauth/signin" + '?' + $.param(params);//alert(JSON.stringify(params));
                window.location = url;
            }
        },
    });

};
