odoo.define('auth_signup.signup', function (require) {
    'use strict';

require('web.dom_ready');

// Disable 'Sign Up' button to prevent user form continuous clicking
if ($('.oe_signup_form').length > 0) {
    $('.oe_signup_form').on('submit', function () {
        $('.o_signup_btn').attr('disabled', 'disabled');
        $('.o_signup_btn').prepend('<i class="fa fa-refresh fa-spin"/> ');
    });
}

});
