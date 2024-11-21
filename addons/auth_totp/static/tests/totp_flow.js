/** @odoo-module **/

import { queryAll } from "@odoo/hoot-dom";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

function openRoot() {
    return [{
        content: "return to client root to avoid race condition",
        trigger: 'body',
        run() {
            document.querySelector("body").classList.add("wait");
            window.location = '/odoo';
        }
    }, {
        content: "wait for client reload",
        trigger: 'body:not(.wait)',
    }];
}
function openUserProfileAtSecurityTab() {
    return [{
        content: 'Open user account menu',
        trigger: '.o_user_menu .dropdown-toggle',
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
        run(helpers) {
            const modal = document.querySelector(".o_dialog");
            if (modal) {
                modal.querySelector("button[name=preference_cancel]").click();
            }
        }
    }, {
        trigger: 'body',
        async run() {
            while (document.querySelector('.o_dialog')) {
                await Promise.resolve();
            }
            this.anchor.classList.add("dialog-closed");
        },
    }, {
        trigger: 'body.dialog-closed',
    }];
}

registry.category("web_tour.tours").add('totp_tour_setup', {
    url: '/odoo',
    steps: () => [...openUserProfileAtSecurityTab(), {
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_enable_wizard]',
    run: "click",
},
{
    trigger: ".modal div:contains(entering your password)",
},
{
    content: "Check that we have to enter enhanced security mode and input password",
    trigger: '[name=password] input',
    run: "edit demo",
}, {
    content: "Confirm",
    trigger: "button:contains(Confirm Password)",
    run: "click",
}, {
    content: "Check the wizard has opened",
    trigger: '.modal li:contains("When requested to do so")',
}, {
    content: "Get secret from collapsed div",
    trigger: `.modal a:contains("Cannot scan it?")`,
    async run(helpers) {
        const secret = this.anchor
            .closest("div")
            .querySelector("[name=secret] span:first-child");
        const copyBtn = secret.querySelector("button");
        if (copyBtn) {
            copyBtn.remove();
        }
        const token = await rpc('/totphook', {
            secret: secret.textContent
        });
        await helpers.edit(token, '[name=code] input');
        document.querySelector("body").classList.add("got-token");
    }
},
{
    trigger: ".modal button.btn-primary:contains(Activate)",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    content: 'wait for rpc',
    trigger: 'body.got-token',
},
...openRoot(),
...openUserProfileAtSecurityTab(),
...closeProfileDialog({
    content: "Check that the button has changed",
    totp_state: true,
}),
]});

registry.category("web_tour.tours").add('totp_login_enabled', {
    url: '/',
    steps: () => [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)',
    run: "click",
}, {
    content: "input login",
    trigger: 'input#login',
    run: "edit demo",
}, {
    content: 'input password',
    trigger: 'input#password',
    run: "edit demo",
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
    run: "click",
}, {
    content: "expect totp screen",
    trigger: 'label:contains(Authentication Code)',
    run: "click",
}, {
    content: "input code",
    trigger: 'input[name=totp_token]',
    async run(helpers) {
        const token = await rpc('/totphook');
        helpers.edit(token);
    }
},
{
    trigger: `button:contains("Log in")`,
    run: "click",
},
{
    content: "check we're logged in",
    trigger: ".o_user_menu .dropdown-toggle",
}]});

registry.category("web_tour.tours").add('totp_login_device', {
    url: '/',
    steps: () => [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)',
    run: "click",
}, {
    content: "input login",
    trigger: 'input#login',
    run: "edit demo",
}, {
    content: 'input password',
    trigger: 'input#password',
    run: "edit demo",
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
    run: "click",
}, {
    content: "expect totp screen",
    trigger: 'label:contains(Authentication Code)',
    run: "click",
}, {
    content: "check remember device box",
    trigger: 'label[for=switch-remember]',
    run: "click",
}, {
    content: "input code",
    trigger: 'input[name=totp_token]',
    async run(helpers) {
        const token = await rpc('/totphook')
        helpers.edit(token);
    }
},
{
    trigger: "button:contains(Log in)",
    run: "click",
},
{
    content: "check we're logged in",
    trigger: ".o_user_menu .dropdown-toggle",
    run: 'click',
}, {
    content: "click the Log out button",
    trigger: '.dropdown-item[data-menu=logout]',
    run: "click",
}, {
    content: "check that we're back on the login page or go to it",
    trigger: 'input#login, a:contains(Log in)',
    run: "edit Test",
}, {
    content: "input login again",
    trigger: 'input#login',
    run: "edit demo",
}, {
    content: 'input password again',
    trigger: 'input#password',
    run: "edit demo",
}, {
    content: "click da button again",
    trigger: 'button:contains("Log in")',
    run: "click",
},  {
    content: "check we're logged in without 2FA",
    trigger: ".o_user_menu .dropdown-toggle",
},
// now go and disable two-factor authentication would be annoying to do in a separate tour
// because we'd need to login & totp again as HttpCase.authenticate can't
// succeed w/ totp enabled
...openUserProfileAtSecurityTab(),
{
    content: "Open totp wizard",
    trigger: 'button[name=action_totp_disable]',
    run: "click",
},
{
    trigger: ".modal div:contains(entering your password)",
},
{
    content: "Check that we have to enter enhanced security mode and input password",
    trigger: ".modal [name=password] input",
    run: "edit demo",
}, {
    content: "Confirm",
    trigger: ".modal button:contains(Confirm Password)",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
...openRoot(),
...openUserProfileAtSecurityTab(),
...closeProfileDialog({
    content: "Check that the button has changed",
    totp_state: false
}),
]});

registry.category("web_tour.tours").add('totp_login_disabled', {
    url: '/',
    steps: () => [{
    content: "check that we're on the login page or go to it",
    trigger: 'input#login, a:contains(Sign in)',
    run: "click",
}, {
    content: "input login",
    trigger: 'input#login',
    run: "edit demo",
}, {
    content: 'input password',
    trigger: 'input#password',
    run: "edit demo",
}, {
    content: "click da button",
    trigger: 'button:contains("Log in")',
    run: "click",
},
// normally we'd end the tour here as it's all we care about but there are a
// bunch of ongoing queries from the loading of the web client which cause
// issues, so go and open the preferences / profile screen to make sure
// everything settles down
...openUserProfileAtSecurityTab(),
// close the dialog if that makes sense
...closeProfileDialog({})
]});

const columns = {};
registry.category("web_tour.tours").add('totp_admin_disables', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    content: 'Go to settings',
    trigger: '[data-menu-xmlid="base.menu_administration"]',
    run: "click",
}, {
    content: 'Wait for page',
    trigger: '.o_menu_brand:contains("Settings")',
}, {
    content: "Open Users menu",
    trigger: '[data-menu-xmlid="base.menu_users"]',
    run: "click",
}, {
    content: "Open Users view",
    trigger: '[data-menu-xmlid="base.menu_action_res_users"]',
    run: "click",
}, {
    content: "Find Demo User",
    trigger: 'td.o_data_cell:contains("demo")',
    run(helpers) {
        const titles = queryAll("tr:first th", { root: this.anchor.closest("table") });
        titles.forEach((el, i) => {
            columns[el.getAttribute('data-name')] = i;
        })
        const row = this.anchor.closest('tr');
        const sel = row.querySelector('.o_list_record_selector input[type=checkbox]');
        helpers.click(sel);
    }
}, {
    content: "Open Actions menu",
    trigger: 'button.dropdown-toggle:contains("Action")',
    run: "click",
}, {
    content: "Select totp remover",
    trigger: 'span.dropdown-item:contains(Disable two-factor authentication)',
    run: "click",
},
{
    trigger: ".modal div:contains(entering your password)",
},
{ // enhanced security yo
    content: "Check that we have to enter enhanced security mode & input password",
    trigger: '.modal [name=password] input',
    run: "edit admin",
}, {
    content: "Confirm",
    trigger: ".modal button:contains(Confirm Password)",
    run: "click",
},
{
    content: "Wait the modal is closed",
    trigger: "body:not(:has(.modal))",
},
{
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(demo)",
    run: "click",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
    run: "click",
}, ...closeProfileDialog({
    content: "check that demo user has been de-totp'd",
    totp_state: false,
}),
]})
