odoo.define('auth_password_policy_signup.policy', function (require) {
"use strict";

require('web.dom_ready');
var policy = require('auth_password_policy');
var PasswordMeter = require('auth_password_policy.Meter');

var $signupForm = $('.oe_signup_form, .oe_reset_password_form');
if (!$signupForm.length) { return; }

// hook in password strength meter
// * requirement is the password field's minlength
// * recommendations are from the module
var $password = $signupForm.find('#password');
var minlength = Number($password.attr('minlength'));
if (isNaN(minlength)) { return; }

var meter = new PasswordMeter(null, new policy.Policy({minlength: minlength}), policy.recommendations);
meter.insertAfter($password);
$password.on('input', function () {
    meter.update($password.val());
});
});
