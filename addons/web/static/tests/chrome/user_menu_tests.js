odoo.define('web.user_menu_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var UserMenu = require('web.UserMenu');

const { Component, tags } = owl;

QUnit.module('chrome', {}, function () {
    QUnit.module('UserMenu');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(4);

        class Parent extends Component {}
        Parent.template = tags.xml`<UserMenu/>`;
        Parent.components = { UserMenu };

        const target = testUtils.prepareTarget();
        const parent = new Parent();
        await parent.mount(target);

        assert.containsOnce(target, '.o_user_menu');
        assert.containsOnce(target, '.o_user_menu > a');
        assert.containsOnce(target, '.o_user_menu > .dropdown-menu');
        assert.containsOnce(target, '.dropdown-item[data-menu="shortcuts"]');

        parent.destroy();
    });
});

});
