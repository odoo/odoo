odoo.define('auth_signup.signup', function (require) {
'use strict';

require('web.dom_ready');
    if (!$('.oe_signup_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_signup_form'");
    }

    // Disable 'Sign Up' button to prevent user for continuous clicking
    $('.oe_signup_form').on('submit', function() {
        $('.o_portal_signup').attr('disabled', 'disabled');
    });
});
