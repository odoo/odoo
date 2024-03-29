/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

registry.category("web_tour.tours").add('totportal_tour_setup', {
    test: true,
    url: '/my/security',
    steps: () => [{
    content: "Open totp wizard",
    trigger: 'button#auth_totp_portal_enable',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: "edit portal", // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check the wizard has opened",
    trigger: 'li:contains("scan the barcode below")',
    run: () => {}
}, {
    content: "Get secret from collapsed div",
    trigger: 'a:contains("Cannot scan it?")',
    run: async function(helpers) {
        const secret = this.anchor
            .closest("div")
            .querySelector('span[name="secret"]').textContent;
        const token = await rpc('/totphook', {
            secret
        });
        helpers.edit(token, 'input[name="code"]');
        helpers.click("button.btn-primary:contains(Activate)");
    }
}, {
    content: "Check that the button has changed",
    trigger: 'button:contains(Disable two-factor authentication)',
    run: () => {}
}]});

registry.category("web_tour.tours").add('totportal_login_enabled', {
    test: true,
    url: '/',
    steps: () => [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: "edit portal",
}, {
    content: 'input password',
    trigger: 'input#password',
    run: "edit portal",
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
        const token = await rpc('/totphook');
        helpers.edit(token);
        // FIXME: is there a way to put the button as its own step trigger without
        //        the tour straight blowing through and not waiting for this?
        helpers.click('button:contains("Log in")');
    }
}, {
    content: "check we're logged in",
    trigger: "h3:contains(My account)",
    run: () => {}
}, {
    content: "go back to security",
    trigger: "a:contains(Security)",
},{
    content: "Open totp wizard",
    trigger: 'button#auth_totp_portal_disable',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: "edit portal", // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check that the button has changed",
    trigger: 'button:contains(Enable two-factor authentication)',
    run: () => {}
}]});

registry.category("web_tour.tours").add('totportal_login_disabled', {
    test: true,
    url: '/',
    steps: () => [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: "edit portal",
}, {
    content: 'input password',
    trigger: 'input#password',
    run: "edit portal",
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
}, {
    content: "check we're logged in",
    trigger: "h3:contains(My account)",
    run: () => {}
}]});
