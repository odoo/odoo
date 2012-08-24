openerp.auth_signup = function(instance) {
    instance.auth_signup = instance.auth_signup || {};
    var _t = instance.web._t;

    instance.web.Login.include({
        start: function() {
            var self = this;
            this.$('a.oe_signup').click(function() {
                var dbname = self.$("form [name=db]").val();
                self.do_action({
                    type: 'ir.actions.client',
                    tag: 'auth_signup.signup',
                    params: {'dbname': dbname},
                    target: 'new',
                    name: 'Sign up'
                });
                return true;
            });
            return this._super();
        },
    });


    instance.auth_signup.Signup = instance.web.Widget.extend({
        template: 'auth_signup.signup',
        init: function(parent, params) {
            this.params = params;
            return this._super();
        },
        start: function() {
            var self = this;
            this.$('input[name=password_confirmation]').keyup(function() {
                var v = $(this).val();
                var $b = self.$('button');
                if (_.isEmpty(v) || self.$('input[name=password]').val() === v) {
                    $b.removeAttr('disabled');
                } else {
                    $b.attr('disabled', 'disabled');
                }
            });

            this.$('form').submit(function(ev) {
                if(ev) {
                    ev.preventDefault();
                }
                var params = {
                    dbname : self.params.dbname,
                    name: self.$('input[name=name]').val(),
                    login: self.$('input[name=email]').val(),
                    password: self.$('input[name=password]').val(),
                };
                var url = "/auth_signup/signup?" + $.param(params);
                window.location = url;
            });
            return this._super();
        }
    });
    instance.web.client_actions.add("auth_signup.signup", "instance.auth_signup.Signup");

};
