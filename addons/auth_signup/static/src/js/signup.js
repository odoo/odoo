odoo.define('auth_signup.signup', function (require) {
    'use strict';

var base = require('web_editor.base');

base.ready().then(function() {
    // Disable 'Sign Up' button to prevent user form continuous clicking
    if ($('.oe_signup_form').length > 0) {
        $('.oe_signup_form').on('submit', function (ev) {
            var $form = $(ev.currentTarget);
            var $btn = $form.find('.oe_login_buttons > button[type="submit"]');
            $btn.attr('disabled', 'disabled');
            $btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
        });
    }
});

});
