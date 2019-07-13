odoo.define('web.user_menu_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var UserMenu = require('web.UserMenu');
var Widget = require('web.Widget');

QUnit.module('chrome', {}, function () {
    QUnit.module('UserMenu');

    QUnit.test('basic rendering', function (assert) {
        assert.expect(3);

        var parent = new Widget();

        testUtils.addMockEnvironment(parent, {});
        var userMenu = new UserMenu(parent);
        userMenu.appendTo($('body'));

        assert.strictEqual($('.o_user_menu').length, 1,
            "should have a user menu in the DOM");
        assert.ok(userMenu.$el.hasClass('o_user_menu'),
            "user menu in DOM should be from user menu widget instantiation");
        assert.strictEqual(userMenu.$('.dropdown-item[data-menu="shortcuts"]').length, 1,
            "should have a 'Shortcuts' item");

        userMenu.destroy();
        parent.destroy();
    });
});

});
