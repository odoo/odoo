odoo.define('auth_signup.signup', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SignUpForm = publicWidget.Widget.extend({
    selector: '.oe_signup_form',
    events: {
        'submit': '_onSubmit',
    },

    start() {
        this._super(...arguments);
        this.$('#login').change(this._onChangeLogin);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubmit: function () {
        var $btn = this.$('.oe_login_buttons > button[type="submit"]');
        $btn.attr('disabled', 'disabled');
        $btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
    },

    /**
     * @private
     */
    _onChangeLogin: function() {
        $(this).val($(this).val().toLocaleLowerCase());
    }
});
});
