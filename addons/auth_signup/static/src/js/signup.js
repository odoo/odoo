odoo.define('auth_signup.signup', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SignUpForm = publicWidget.Widget.extend({
    selector: '.oe_signup_form',
    events: {
        'submit': '_onSubmit',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubmit: function () {
        var $btn = this.$('.oe_login_buttons > button[type="submit"]');
        if ($btn.prop("disabled")) {
            return;
        }
        $btn.attr('disabled', 'disabled');
        $btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
    },
});
});
