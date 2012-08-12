openerp.auth_oauth = function(instance) {

    var QWeb = instance.web.qweb;

    instance.web.Login = instance.web.Login.extend({
        start: function(parent, params) {
            this._super.apply(this, arguments);
            var self = this;
            self.$element.on('click', '.oe_login_oauth a', this.on_google_oauth);
        },
        on_google_oauth: function(ev) {
            var url = this._oauth_url();
            window.location = url;
        },
        _oauth_url: function() {
            var endpoint = 'https://accounts.google.com/o/oauth2/auth';
            var params = {            
                response_type: 'token',
                client_id: '108010644258-duuhmp6pu7li4tsmnqg7j9rvdeklg0ki.apps.googleusercontent.com',
                redirect_uri: 'https://localhost/',
                scope: 'https://www.googleapis.com/auth/userinfo.email',
                state: 'TEST',
            };
            var url = endpoint + '?' + $.param(params);
            return url;
        },
        // do_warn: function(title, msg) {
        // },
        // reset_error_message: function() {
        // }
    });

    instance.web.WebClient = instance.web.WebClient.extend({
        start: function() {
            this._super.apply(this, arguments);
            // console.log($.deparam(window.location.hash));
            var params = $.deparam(window.location.hash);
            if (params.hasOwnProperty('access_token')) {
                console.log(params);
                // Do login using Google User credentials
                var url = {
                    
                };
            }
        },
        bind_hashchange: function() {
            var state = $.bbq.getState(true);
            if (state.hasOwnProperty("access_token")) {
                state.action = "login";
                $.bbq.setState(state);
            }
            this._super();

        },
        // on_hashchange: function(event)  {                        
        //     console.log(event);
        //     this._super.apply(this, arguments);
        // },
    });

};

// https://accounts.google.com/o/oauth2/auth?state=%2Fprofile&redirect_uri=http%3A%2F%2Foauth2-login-demo.appspot.com%2Fcode&response_type=code&client_id=812741506391.apps.googleusercontent.com&approval_prompt=force&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile