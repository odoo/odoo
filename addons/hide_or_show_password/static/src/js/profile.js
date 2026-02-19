odoo.define('hide_or_show_password.ChangePassword', function (require) {
    "use strict";
    
    var ChangePassword = require('web.ChangePassword');
    var core = require('web.core');
    var web_client = require('web.web_client');

    var _t = core._t;
    
    ChangePassword.include({
        template: "ShowAndHidePassword",
        
        /**
         * @fixme: weird interaction with the parent for the $buttons handling
         *
         * @override
         * @returns {Promise}
         */
        start: function () {
            var self = this;
            web_client.set_title(_t("Change Password"));

            var $showPasswordButton = self.$('.show__password')
            var $showPasswordInput = self.$('.o_input')
            for (let i=0; i<3; i++) {
                $showPasswordButton.eq(i).click(function() {
                    if($showPasswordInput.eq(i).attr('type') == 'password'){
                        $showPasswordButton.eq(i).removeClass('fa-eye').addClass('fa-eye-slash');
                        $showPasswordInput.eq(i).attr('type', 'text')
                    }else{
                        $showPasswordButton.eq(i).removeClass('fa-eye-slash').addClass('fa-eye');
                        $showPasswordInput.eq(i).attr('type', 'password')
                    }
                })
            }

            var $button = self.$('.oe_form_button');
            $button.appendTo(this.getParent().$footer);
            $button.eq(1).click(function () {
                self.$el.parents('.modal').modal('hide');
            });
            $button.eq(0).click(function () {
                self._rpc({
                        route: '/web/session/change_password',
                        params: {
                            fields: $('form[name=change_password_form]').serializeArray()
                        }
                    })
                    .then(function (result) {
                        if (result.error) {
                            self.displayNotification({
                                message: result.error,
                                type: 'danger'
                            });
                        } else {
                            self.do_action('logout');
                        }
                    });
            });
        },
    })
    
});
    