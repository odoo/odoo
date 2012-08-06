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

                var cnx = instance.connection;
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
                type:'ir.actions.act_window',
                res_model: 'auth.signup',
                views: [[false, 'form']],
                target: 'new',
                name: 'Sign Up'
            }, function() {
                // mmh, no way to have access to dialog befor close...
                // TODO autolog user
                console.log('onclose', this, arguments);
            });
        }
    });

};
