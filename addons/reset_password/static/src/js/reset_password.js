openerp.reset_password = function(instance) {
    var _t = instance.web._t;
    instance.web.Login.include({
        start: function() {
            var $e = this.$element;
            $e.find('.oe_login_switch a').click(function() {
                $e.find('.oe_login_switch').toggle();
                var $m = $e.find('form input[name=is_reset_pw]');
                $m.attr('checked', !$m.is(':checked'));
            });
            return this._super();
        },
        on_submit: function(ev) {
            if(ev) {
                ev.preventDefault();
            }

            var $e = this.$element;
            var db = $e.find("form [name=db]").val();
            if (!db) {
                this.do_warn(_t("Login"), _t("No database selected !"));
                return false;
            }
            
            var $m = $e.find('form input[name=is_reset_pw]');
            if ($m.is(':checked')) {
                var email = $e.find('form input[name=email]').val()
                return this.do_reset_password(db, email);
            } else {
                return this._super(ev);
            }
        },

        do_reset_password: function(db, email) {
            var self = this;
            instance.connection.session_authenticate(db, 'anonymous', 'anonymous', true).pipe(function () {
                var func = new instance.web.Model("res.users").get_func("send_reset_password_request");
                return func(email).then(function(res) {
                    // show message
                    self.do_notify(_t('Reset Password'), _.str.sprintf(_t('We have sent an email to %s with further instructions'), email), true);
                }, function(error, event) {
                    // no traceback please
                    event.preventDefault();
                });
            }).fail(function(error, event) {
                // cannot log as anonymous or reset_password not installed
                self.do_warn(_t('Reset Password'), _.str.sprintf(_t('Reset Password functionnality is not available for database %s'), db), true);
            });
        },
    });

    instance.reset_password = {};
    instance.reset_password.ResetPassword = instance.web.Widget.extend({
        init: function(parent, params) {
            this._super(parent);
            this.token = (params && params.token) || false;
        },
        start: function() {
            this.do_action({
                name: 'Reset Password',
                type: 'ir.actions.act_window',
                context: {default_token: this.token},
                res_model: 'reset_password.wizard',
                target: 'new',
                views: [[false, 'form']],
            });

        }
    });


    instance.web.client_actions.add("reset_password", "instance.reset_password.ResetPassword");


};
