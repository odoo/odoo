openerp.auth_signup = function(instance) {
    instance.auth_signup = instance.auth_signup || {};
    var _t = instance.web._t;

    instance.web.Login.include({
        start: function() {
            var self = this;
            var d = this._super();

            // to switch between the signup and regular login form
            this.$('a.oe_signup_signup').click(function() {
                self.$el.addClass("oe_login_signup");
            });
            this.$('a.oe_signup_back').click(function() {
                self.$el.removeClass("oe_login_signup");
                delete self.params.token;
            });

            // if there is an error message in params, show it then forget it
            if (self.params.error_message) {
                this.show_error(self.params.error_message);
                delete self.params.error_message;
            }

            // in case of a signup, retrieve the user information from the token
            if (self.params.db && self.params.token) {
                d = self.rpc("/auth_signup/retrieve", {dbname: self.params.db, token: self.params.token})
                        .done(self.on_token_loaded)
                        .fail(self.on_token_failed);
            }
            return d;
        },
        on_token_loaded: function(result) {
            // switch to signup mode
            this.$el.addClass("oe_login_signup");
            // select the right the database
            this.selected_db = result.db;
            this.on_db_loaded({db_list: [result.db]});
            // set the name and login of user
            this.$("form input[name=name]").val(result.name).attr("readonly", "readonly");
            if (result.login) {
                this.$("form input[name=login]").val(result.login).attr("readonly", "readonly");
            } else {
                this.$("form input[name=login]").val(result.email);
            }
            this.$("form input[name=password]").val("");
            this.$("form input[name=confirm_password]").val("");
        },
        on_token_failed: function(result, ev) {
            if (ev) {
                ev.preventDefault();
            }
            this.show_error("Invalid signup token");
            delete this.params.db;
            delete this.params.token;
        },
        on_submit: function(ev) {
            if (ev) {
                ev.preventDefault();
            }
            if (this.$el.hasClass("oe_login_signup")) {
                // signup user (or reset password)
                var db = this.$("form [name=db]").val();
                var name = this.$("form input[name=name]").val();
                var login = this.$("form input[name=login]").val();
                var password = this.$("form input[name=password]").val();
                var confirm_password = this.$("form input[name=confirm_password]").val();
                if (!db) {
                    this.do_warn("Login", "No database selected !");
                    return false;
                } else if (!name) {
                    this.do_warn("Login", "Please enter a name.")
                    return false;
                } else if (!login) {
                    this.do_warn("Login", "Please enter a username.")
                    return false;
                } else if (!password || !confirm_password) {
                    this.do_warn("Login", "Please enter a password and confirm it.")
                    return false;
                } else if (password !== confirm_password) {
                    this.do_warn("Login", "Passwords do not match; please retype them.")
                    return false;
                }
                var params = {
                    dbname : db,
                    token: this.params.token || "",
                    name: name,
                    login: login,
                    password: password,
                };
                var url = "/auth_signup/signup?" + $.param(params);
                window.location = url;
            } else {
                // regular login
                this._super(ev);
            }
        },
    });

};
