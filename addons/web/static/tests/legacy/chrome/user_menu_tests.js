odoo.define('web.user_menu_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var UserMenu = require('web.UserMenu');
var Widget = require('web.Widget');

QUnit.module('chrome', {}, function () {
    QUnit.module('UserMenu');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(3);

        var parent = new Widget();

        await testUtils.mock.addMockEnvironment(parent, {});
        var userMenu = new UserMenu(parent);
        await userMenu.appendTo($('body'));

        assert.strictEqual($('.o_user_menu').length, 1,
            "should have a user menu in the DOM");
        assert.hasClass(userMenu.$el,'o_user_menu',
            "user menu in DOM should be from user menu widget instantiation");
        assert.containsOnce(userMenu, '.dropdown-item[data-menu="shortcuts"]',
            "should have a 'Shortcuts' item");

        userMenu.destroy();
        parent.destroy();
    });
});

});
