odoo.define('auth_totp.tours', function(require) {
"use strict";

const tour = require('web_tour.tour');
const ajax = require('web.ajax');

function openRoot() {
    return [{
        content: "return to client root to avoid race condition",
        trigger: 'body',
        run() {
            $('body').addClass('wait');
            window.location = '/web';
        }
    }, {
        content: "wait for client reload",
        trigger: 'body:not(.wait)',
        run() {}
    }];
}
function openUserProfileAtSecurityTab() {
    return [{
        content: 'Open user account menu',
        trigger: '.o_user_menu .oe_topbar_name',
        run: 'click',
    }, {
        content: "Open preferences / profile screen",
        trigger: '[data-menu=settings]',
        run: 'click',
    }, {
        content: "Switch to security tab",
        trigger: 'a[role=tab]:contains("Account Security")',
        run: 'click',
    }];
}

tour.register('totp_tour_setup', {
    test: true,
    url: '/web'
}, [...openUserProfileAtSecurityTab(), {
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_enable_wizard]',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: 'text demo', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check the wizard has opened",
    trigger: 'li:contains("When requested to do so")',
    run: () => {}
}, {
    content: "Get secret from collapsed div",
    trigger: 'a:contains("Cannot scan it?")',
    run(helpers) {
        const $secret = this.$anchor.closest('div').find('span[name=secret]');
        const $copyBtn = $secret.find('button');
        $copyBtn.remove();
        const secret = $secret.text();
        ajax.jsonRpc('/totphook', 'call', {
            secret
        }).then((token) => {
            helpers._text(helpers._get_action_values('input[name=code]'), token);
            helpers._click(helpers._get_action_values('button.btn-primary:contains(Activate)'));
            $('body').addClass('got-token')
        });
    }
}, {
    content: 'wait for rpc',
    trigger: 'body.got-token',
    run() {}
},
...openRoot(),
...openUserProfileAtSecurityTab(),
{
    content: "Check that the button has changed",
    trigger: 'button[name=action_totp_disable]',
    run: () => {}
}]);

tour.register('totp_login_enabled', {
    test: true,
    url: '/'
}, [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: 'text demo',
}, {
    content: 'input password',
    trigger: 'input#password',
    run: 'text demo',
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
}, {
    content: "expect totp screen",
    trigger: 'label:contains(Authentication Code)',
}, {
    content: "input code",
    trigger: 'input[name=totp_token]',
    run(helpers) {
        ajax.jsonRpc('/totphook', 'call', {}).then((token) => {
            helpers._text(helpers._get_action_values(), token);
            // FIXME: is there a way to put the button as its own step trigger without
            //        the tour straight blowing through and not waiting for this?
            helpers._click(helpers._get_action_values('button:contains("Log in")'));
        });
    }
}, {
    content: "check we're logged in",
    trigger: ".o_user_menu .oe_topbar_name",
    run: () => {}
}]);

tour.register('totp_login_device', {
    test: true,
    url: '/'
}, [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: 'text demo',
}, {
    content: 'input password',
    trigger: 'input#password',
    run: 'text demo',
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
}, {
    content: "expect totp screen",
    trigger: 'label:contains(Authentication Code)',
}, {
    content: "check remember device box",
    trigger: 'label[for=switch-remember]',
}, {
    content: "input code",
    trigger: 'input[name=totp_token]',
    run(helpers) {
        ajax.jsonRpc('/totphook', 'call', {}).then((token) => {
            helpers._text(helpers._get_action_values(), token);
            // FIXME: is there a way to put the button as its own step trigger without
            //        the tour straight blowing through and not waiting for this?
            helpers._click(helpers._get_action_values('button:contains("Log in")'));
        });
    }
}, {
    content: "check we're logged in",
    trigger: ".o_user_menu .oe_topbar_name",
    run: 'click',
}, {
    content: "click the Log out button",
    trigger: '.dropdown-item[data-menu=logout]',
}, {
    content: "check that we're back on the login page or go to it",
    trigger: 'input#login, a:contains(Log in)'
}, {
    content: "input login again",
    trigger: 'input#login',
    run: 'text demo',
}, {
    content: 'input password again',
    trigger: 'input#password',
    run: 'text demo',
}, {
    content: "click da button again",
    trigger: 'button:contains("Log in")',
},  {
    content: "check we're logged in without 2FA",
    trigger: ".o_user_menu .oe_topbar_name",
    run: () => {}
},
// now go and disable two-factor authentication would be annoying to do in a separate tour
// because we'd need to login & totp again as HttpCase.authenticate can't
// succeed w/ totp enabled
...openUserProfileAtSecurityTab(),
{
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_disable]',
}, {
    content: "Check that we have to enter enhanced security mode",
    trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: 'text demo', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
},
...openRoot(),
...openUserProfileAtSecurityTab(),
{
    content: "Check that the button has changed",
    trigger: 'button[name=action_totp_enable_wizard]',
    run: () => {}
}]);

tour.register('totp_login_disabled', {
    test: true,
    url: '/'
}, [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)'
}, {
    content: "input login",
    trigger: 'input#login',
    run: 'text demo',
}, {
    content: 'input password',
    trigger: 'input#password',
    run: 'text demo',
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
},
// normally we'd end the tour here as it's all we care about but there are a
// bunch of ongoing queries from the loading of the web client which cause
// issues, so go and open the preferences / profile screen to make sure
// everything settles down
...openUserProfileAtSecurityTab(),
]);

const columns = {};
tour.register('totp_admin_disables', {
    test: true,
    url: '/web'
}, [tour.stepUtils.showAppsMenuItem(), {
    content: 'Go to settings',
    trigger: '[data-menu-xmlid="base.menu_administration"]'
}, {
    content: 'Wait for page',
    trigger: '.o_menu_brand:contains("Settings")',
    run: () => {}
}, {
    content: "Open Users menu",
    trigger: '[data-menu-xmlid="base.menu_users"]'
}, {
    content: "Open Users view",
    trigger: '[data-menu-xmlid="base.menu_action_res_users"]',
    run: function (helpers) {
        // funny story: the users view we're trying to reach, sometimes we're
        // already there, but if we re-click the next step executes before the
        // action has the time to re-load, the one after that doesn't, and our
        // selection get discarded by the action reloading, so here try to
        // see if we're already on the users action through the breadcrumb and
        // just close the menu if so
        const $crumb = $('.breadcrumb');
        if ($crumb.text().indexOf('Users') === -1) {
            // on general settings page, click menu
            helpers.click();
        } else {
            // else close menu
            helpers.click($('[data-menu-xmlid="base.menu_users"]'));
        }
    }
}, {
    content: "Find Demo User",
    trigger: 'td.o_data_cell:contains("demo")',
    run: function (helpers) {
        const $titles = this.$anchor.closest('table').find('tr:first th');
        for (let i=0; i<$titles.length; ++i) {
            columns[$titles[i].getAttribute('data-name')] = i;
        }
        const $row = this.$anchor.closest('tr');
        const sel = $row.find('.o_list_record_selector input[type=checkbox]');
        helpers.click(sel);
    }
}, {
    content: "Open Actions menu",
    trigger: 'button.dropdown-toggle:contains("Action")'
}, {
    content: "Select totp remover",
    trigger: 'a.dropdown-item:contains(Disable two-factor authentication)'
}, { // enhanced security yo
    content: "Check that we have to enter enhanced security mode",
trigger: 'div:contains("enter your password")',
    run: () => {},
}, {
    content: "Input password",
    trigger: '[name=password]',
    run: 'text admin', // FIXME: better way to do this?
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(demo)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, {
    content: "check that demo user has been de-totp'd",
    trigger: "button[name=action_totp_enable_wizard]",
}])
});
