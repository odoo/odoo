odoo.define('web.user_menu_tests', function (require) {
"use strict";

const testUtils = require('web.test_utils');
const UserMenu = require('web.UserMenu');

const { createComponent } = testUtils;

QUnit.module('chrome', {}, function () {
    QUnit.module('UserMenu');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(3);

        const userMenu = await createComponent(UserMenu, {});
        await userMenu.mount(document.querySelector("body"));

        assert.strictEqual($('.o_user_menu').length, 1,
            "should have a user menu in the DOM");
        assert.hasClass(userMenu.el, 'o_user_menu',
            "user menu in DOM should be from user menu widget instantiation");
        assert.containsOnce(userMenu, '.dropdown-item[data-menu="shortcuts"]',
            "should have a 'Shortcuts' item");

        userMenu.destroy();
    });
});

});
