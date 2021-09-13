odoo.define('auth_totp_mail.tours', function(require) {
"use strict";

const tour = require('web_tour.tour');

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

tour.register('totp_admin_self_invite', {
    test: true,
    url: '/web'
}, [tour.stepUtils.showAppsMenuItem(), ...openAccountSettingsTab(), {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(admin)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, {
    content: "check that user cannot invite himself to use 2FA.",
    trigger: "body",
    run: function () {
        var $inviteBtn = $('button:contains(Invite to use 2FA)');
        if ($inviteBtn.hasClass('o_invisible_modifier')) {
            $('body').addClass('CannotInviteYourself');
        }
    }
}, {
    content: "check that user cannot invite themself.",
    trigger: "body.CannotInviteYourself"
}]);

tour.register('totp_admin_invite', {
    test: true,
    url: '/web'
}, [tour.stepUtils.showAppsMenuItem(), ...openAccountSettingsTab(), {
    content: "open the user's form",
    trigger: "td.o_data_cell:contains(demo)",
}, {
    content: "go to Account security Tab",
    trigger: "a.nav-link:contains(Account Security)",
}, {
    content: "check that demo user can be invited to use 2FA.",
    trigger: "button:contains(Invite to use 2FA)",
}]);

});