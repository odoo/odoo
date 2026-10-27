/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

function openAccountSettingsTab() {
    return [{
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
    }];
}

registry.category("web_tour.tours").add('totp_admin_self_invite', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), ...openAccountSettingsTab(), {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(admin)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, {
    content: "check that user cannot invite themselves to use 2FA.",
    trigger: "body",
    run: function () {
        const inviteBtn = $('button:contains(Invite to use 2FA)')[0];
        if (!inviteBtn) {
            $('body').addClass('CannotInviteYourself');
        }
    }
}, {
    content: "check that user cannot invite themself.",
    trigger: "body.CannotInviteYourself",
    isCheck: true,
}]});

registry.category("web_tour.tours").add('totp_admin_invite', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), ...openAccountSettingsTab(), {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(test_user)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, {
    content: "check that test_user user can be invited to use 2FA.",
    trigger: "button:contains(Invite to use 2FA)",
    isCheck: true,
}]});
