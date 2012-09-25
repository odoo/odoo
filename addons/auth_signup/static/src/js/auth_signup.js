openerp.auth_signup = function(instance) {
    instance.auth_signup = instance.auth_signup || {};
    var _t = instance.web._t;

    instance.web.Login.include({
        start: function() {
            var self = this;
            var d = this._super();
            // hide the signup fields in the case of a regular login
            self.on_change_mode()
            self.$("form input[name=signup]").click(self.on_change_mode);
            // in case of a signup, retrieve the user information from the token
            if (self.params.db && self.params.token) {
                d = self.rpc("/auth_signup/retrieve", {dbname: self.params.db, token: self.params.token})
                        .done(self.on_token_loaded)
                        .fail(self.on_token_failed);
            }
            return d;
        },
        on_token_loaded: function(result) {
            // set the name and login of user
            this.selected_db = result.db;
            this.on_db_loaded({db_list: [result.db]});
            this.$("form input[name=signup]").val(result.login ? [] : ["check_signup"]);
            this.$("form input[name=name]").val(result.name);
            this.$("form input[name=login]").val(result.login || result.email);
            this.$("form input[name=password]").val("");
            this.$("form input[name=confirm_password]").val("");
            this.on_change_mode();
        },
        on_token_failed: function(result) {
            // currently does nothing
        },
        on_change_mode: function() {
            // 'mode' has changed: regular login, sign up, reset password
            var is_signup = this.$("input[name=signup]:checked").val();
            this.$(".oe_signup").toggleClass('oe_form_invisible', false && !is_signup);
            return true;            
        },
        on_submit: function(ev) {
            if (ev) {
                ev.preventDefault();
            }
            if (this.params.token || this.$("input[name=signup]:checked").val()) {
                // signup user (or reset password)
                var db = this.params.db;
                var name = this.$("form input[name=name]").val();
                var login = this.$("form input[name=login]").val();
                var password = this.$("form input[name=password]").val();
                var confirm_password = this.$("form input[name=confirm_password]").val();

                if (password && password === confirm_password) {
                    var params = {
                        dbname : db,
                        token: this.params.token,
                        name: name,
                        login: login,
                        password: password,
                    };
                    var url = "/auth_signup/signup?" + $.param(params);
                    window.location = url;
                } else {
                    alert('Incorrect password; please retype your password.');
                }
            } else {
                // regular login
                this._super(ev);
            }
        },
    });

};
