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

/**
 * Checks that the TOTP button is in the specified state (true = enabled =
 * can disable, false = disabled = can enable), then closes the profile dialog
 * if it's one (= hr not installed).
 *
 * If no totp state is provided, just checks that the toggle exists.
 */
function closeProfileDialog({content, totp_state}) {
    let trigger;
    switch (totp_state) {
    case true: trigger = 'button[name=action_totp_disable]'; break;
    case false: trigger = 'button[name=action_totp_enable_wizard]'; break;
    case undefined: trigger = 'button.o_auth_2fa_btn'; break;
    default: throw new Error(`Invalid totp state ${totp_state}`)
    }

    return [{
        content,
        trigger,
        run() {
            const $modal = this.$anchor.parents('.o_dialog_container');
            if ($modal.length) {
                $modal.find('button[name=preference_cancel]').click()
            }
        }
    }, {
        trigger: 'body',
        async run() {
            while (document.querySelector('.o_dialog_container .o_dialog')) {
                await Promise.resolve();
            }
            this.$anchor.addClass('dialog-closed');
        },
    }, {
        trigger: 'body.dialog-closed',
        run() {},
    }];
}

tour.register('totp_tour_setup', {
    test: true,
    url: '/web'
}, [...openUserProfileAtSecurityTab(), {
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_enable_wizard]',
}, {
    content: "Check that we have to enter enhanced security mode and input password",
    extra_trigger: 'div:contains("enter your password")',
    trigger: '[name=password] input',
    run: 'text demo',
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "Check the wizard has opened",
    trigger: 'li:contains("When requested to do so")',
    run() {}
}, {
    content: "Get secret from collapsed div",
    trigger: 'a:contains("Cannot scan it?")',
    async run(helpers) {
        const $secret = this.$anchor.closest('div').find('[name=secret] > span');
        const $copyBtn = $secret.find('button');
        $copyBtn.remove();
        const token = await ajax.jsonRpc('/totphook', 'call', {
            secret: $secret.text()
        });
        helpers.text(token, '[name=code] input');
        helpers.click('button.btn-primary:contains(Activate)');
        $('body').addClass('got-token')
    }
}, {
    content: 'wait for rpc',
    trigger: 'body.got-token',
    run() {}
},
...openRoot(),
...openUserProfileAtSecurityTab(),
...closeProfileDialog({
    content: "Check that the button has changed",
    totp_state: true,
}),
]);

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
    async run(helpers) {
        // TODO: if tours are ever async-aware the click should get moved out,
        //       but currently there's no great way to make the tour wait until
        //       we've retrieved and set the token: `:empty()` is aboutthe text
        //       content of the HTML element, not the JS value property. We
        //       could set a class but that's really no better than
        //       procedurally clicking the button after we've set the input.
        const token = await ajax.jsonRpc('/totphook', 'call', {});
        helpers.text(token);
        helpers.click('button:contains("Login")');
    }
}, {
    content: "check we're logged in",
    trigger: ".o_user_menu .oe_topbar_name",
    run() {}
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
    async run(helpers) {
        const token = await ajax.jsonRpc('/totphook', 'call', {})
        helpers.text(token);
        helpers.click('button:contains("Login")');
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
    run() {}
},
// now go and disable two-factor authentication would be annoying to do in a separate tour
// because we'd need to login & totp again as HttpCase.authenticate can't
// succeed w/ totp enabled
...openUserProfileAtSecurityTab(),
{
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_disable]',
}, {
    content: "Check that we have to enter enhanced security mode and input password",
    extra_trigger: 'div:contains("enter your password")',
    trigger: '[name=password] input',
    run: 'text demo',
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
},
...openRoot(),
...openUserProfileAtSecurityTab(),
...closeProfileDialog({
    content: "Check that the button has changed",
    totp_state: false
}),
]);

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
// close the dialog if that makes sense
...closeProfileDialog({})
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
    run() {}
}, {
    content: "Open Users menu",
    trigger: '[data-menu-xmlid="base.menu_users"]'
}, {
    content: "Open Users view",
    trigger: '[data-menu-xmlid="base.menu_action_res_users"]',
    run(helpers) {
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
    run(helpers) {
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
    trigger: 'span.dropdown-item:contains(Disable two-factor authentication)'
}, { // enhanced security yo
    content: "Check that we have to enter enhanced security mode & input password",
    extra_trigger: 'div:contains("enter your password")',
    trigger: '[name=password] input',
    run: 'text admin',
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
}, {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(demo)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, ...closeProfileDialog({
    content: "check that demo user has been de-totp'd",
    totp_state: false,
}),
])
});
