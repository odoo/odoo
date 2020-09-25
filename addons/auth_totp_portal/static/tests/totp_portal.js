odoo.define('auth_totp_portal.tours', function(require) {
"use strict";

const tour = require('web_tour.tour');
const ajax = require('web.ajax');

tour.register('totportal_tour_setup', {
    test: true,
    url: '/my/security'
}, [{
    content: "Open totp wizard",
    trigger: 'button#auth_totp_portal_enable',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("confirm your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: 'text portal', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check the wizard has opened",
    trigger: 'div:contains("Scan the image below")',
    run: () => {}
}, {
    content: "Get secret from collapsed div",
    trigger: 'a:contains("show the code")',
    run: async function(helpers) {
        const secret = this.$anchor.closest('div').find('code').text();
        const token = await ajax.jsonRpc('/totphook', 'call', {
            secret
        });
        helpers._text(helpers._get_action_values('input[name=code]'), token);
        helpers._click(helpers._get_action_values('button.btn-primary:contains(Enable)'));
    }
}, {
    content: "Check that the button has changed",
    trigger: 'button:contains(Disable two-factor authentication)',
    run: () => {}
}]);

tour.register('totportal_login_enabled', {
    test: true,
    url: '/'
}, [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: 'text portal',
}, {
    content: 'input password',
    trigger: 'input#password',
    run: 'text portal',
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
}, {
    content: "expect totp screen",
    trigger: 'label:contains(Authentication Code)',
}, {
    content: "input code",
    trigger: 'input[name=totp_token]',
    run: async function (helpers) {
        const token = await ajax.jsonRpc('/totphook', 'call', {});
        helpers._text(helpers._get_action_values(), token);
        // FIXME: is there a way to put the button as its own step trigger without
        //        the tour straight blowing through and not waiting for this?
        helpers._click(helpers._get_action_values('button:contains("Verify")'));
    }
}, {
    content: "check we're logged in",
    trigger: "h3:contains(Documents)",
    run: () => {}
}, {
    content: "go back to security",
    trigger: "a:contains(Security)",
},{
    content: "Open totp wizard",
    trigger: 'button#auth_totp_portal_disable',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("confirm your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: 'text portal', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check that the button has changed",
    trigger: 'button:contains(Enable two-factor authentication)',
    run: () => {}
}]);

tour.register('totportal_login_disabled', {
    test: true,
    url: '/'
}, [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: 'text portal',
}, {
    content: 'input password',
    trigger: 'input#password',
    run: 'text portal',
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
}, {
    content: "check we're logged in",
    trigger: "h3:contains(Documents)",
    run: () => {}
}]);
});
