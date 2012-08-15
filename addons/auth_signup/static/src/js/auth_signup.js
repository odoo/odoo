openerp.auth_signup = function(instance) {
    var _t = instance.web._t;

    instance.web.Login.include({
        start: function() {
            var self = this;

            this.$('a.oe_signup').click(function() {
                var db = self.$("form [name=db]").val();
                if (!db) {
                    self.do_warn(_t("Login"), _t("No database selected!"));
                    return false;
                }

                var cnx = instance.session;
                if (cnx.session_is_valid()) {
                    self._signup();
                } else {
                    cnx.session_authenticate(db, 'anonymous', 'anonymous', true).then(function() {
                        self._signup();
                    }).fail(function(error, event) {
                        console.log(error);
                        // cannot log as anonymous or auth_signup not installed
                        self.do_warn(_t('Sign Up'), _.str.sprintf(_t('Signup functionnality is not available for database %s'), db), true);
                    });
                }
                return true;
            });
            return this._super();

        },

        _signup: function() {
            this.do_action({
                type: 'ir.actions.client',
                tag: 'auth_signup.signup',
                target: 'new',
                name: 'Sign up'
            });
        }
    });


    instance.auth_signup = instance.auth_signup || {};
    instance.auth_signup.Signup = instance.web.Widget.extend({
        template: 'auth_signup.signup',
        init: function() {
            this._super.apply(this, arguments);
            this.dataset = new instance.web.DataSet(this, 'auth.signup');
        },
        start: function() {
            var self = this;
            this.$('input[type=password]').change(function() {
                var v = $(this).val();
                var e = !_.isEmpty(v);
                if (e) {
                    e =_.all(self.$('input[type=password]'), function(i) {
                        return $(i).val() === v;
                    });
                }
                var $b = self.$('button');
                if (e) {
                    $b.removeAttr('disabled');
                } else {
                    $b.attr('disabled', 'disabled');
                }
            });

            this.$('form').submit(function(ev) {
                if(ev) {
                    ev.preventDefault();
                }
                var name = self.$('input[name=name]').val();
                var email = self.$('input[name=email]').val();
                var password = self.$('input[name=password]').val();

                self.dataset.create({
                    name: name,
                    email: email,
                    password: password
                }, function() {
                    self.do_action({
                        type: 'ir.actions.client',
                        tag: 'login',
                        params: {
                            db: instance.session.db,
                            login: email,
                            password: password,
                            login_successful: function() {
                                self.do_action('home');
                            }
                        }
                    });
                });
                return false;

            });
            return $.when(this._super());
        }

    });
    instance.web.client_actions.add("auth_signup.signup", "instance.auth_signup.Signup");


};
