odoo.define('web.dropdown_menu_tests', function (require) {
"use strict";

var DropdownMenu = require('web.DropdownMenu');
var testUtils = require('web.test_utils');

function createDropdownMenu(dropdownTitle, groups, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new DropdownMenu(null, dropdownTitle, groups);
    testUtils.addMockEnvironment(menu, params);
    menu.appendTo(target);
    return menu;
}

QUnit.module('Web', {
    beforeEach: function () {
        this.items = [
            {
                isActive: false,
                isOpen: false,
                description: 'Some Item',
                itemId: 1,
                groupId: 1,
            },
            {
                isActive: true,
                description: 'Some other Item',
                itemId: 2,
                options: [],
                isRemovable: true,
                groupId: 2,
            },
        ];
        this.dropdownHeader = {
            title: "Menu",
            icon: "fa fa-bars",
        };
    },
}, function () {
    QUnit.module('DropdownMenu');

    QUnit.test('simple rendering', function (assert) {
        assert.expect(2);

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items);
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 4, 'should have 4 elements counting the dividers');
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').eq(1).text().trim(), 'Some Item',
            'first element should have "Some Item" description');
        dropdownMenu.destroy();
    });

    QUnit.test('click on an item should toggle item', function (assert) {
        assert.expect(9);

        var eventNumber = 0;

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items, {
            intercepts: {
                menu_item_toggled: function (ev) {
                    eventNumber++;
                    assert.strictEqual(ev.data.itemId, 1);
                    if (eventNumber === 1) {
                        assert.strictEqual(ev.data.isActive, true);
                    } else {
                        assert.strictEqual(ev.data.isActive, false);
                    }
                },
            },
        });
        dropdownMenu.$('button:first').click();
        assert.ok(!dropdownMenu.$('.o_menu_item:first > .dropdown-item').hasClass('selected'));
        dropdownMenu.$('.o_menu_item a').first().click();
        assert.ok(dropdownMenu.$('.o_menu_item:first > .dropdown-item').hasClass('selected'));
        assert.ok(dropdownMenu.$('.o_menu_item:first').is(':visible'),
            'item should still be visible');
        dropdownMenu.$('.o_menu_item a').first().click();
        assert.ok(!dropdownMenu.$('.o_menu_item:first > .dropdown-item').hasClass('selected'));
        assert.ok(dropdownMenu.$('.o_menu_item:first').is(':visible'),
            'item should still be visible');

        dropdownMenu.destroy();
    });

    QUnit.test('click on an item should not change url', function (assert) {
        assert.expect(0);

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items);
        dropdownMenu.$el.click(function () {
            // we do not want a click to get out and change the url, for example
            throw new Error('No click should get out of the dropdown menu');
        });
        dropdownMenu.$('.o_menu_item a').first().click();

        dropdownMenu.destroy();
    });

    QUnit.test('options rendering', function (assert) {
        assert.expect(3);

        this.items[0].options = [{optionId: 1, description: "First Option", groupId: 1}, {optionId: 2, description: "Second Option", groupId: 1}];

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items);
        // open dropdown
        dropdownMenu.$('button:first').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 4);
        // open options menu
        dropdownMenu.$('span.fa-caret-right').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 7);
        // close options menu
        dropdownMenu.$('span.fa-caret-down').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 4);

        dropdownMenu.destroy();
    });

    QUnit.test('close menu closes also submenu', function (assert) {
        assert.expect(2);

        this.items[0].options = [{optionId: 1, description: "First Option"}, {optionId: 2, description: "Second Option"}];

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items);
        dropdownMenu.$('button:first').click();
        // open options menu
        dropdownMenu.$('span.fa-caret-right').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 7);
        dropdownMenu.$('button:first').click();
        dropdownMenu.$('button:first').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 4);

        dropdownMenu.destroy();
    });

    QUnit.test('click on an option should toggle options and item states properly', function (assert) {
        assert.expect(22);

        this.items[0].options = [{optionId: 1, description: "First Option"}, {optionId: 2, description: "Second Option"}];

        var eventNumber = 0;

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items, {
            intercepts: {
                menu_item_toggled: function (ev) {
                    eventNumber++;
                    if (eventNumber === 1) {
                        assert.strictEqual(ev.data.itemId, 1);
                        assert.strictEqual(ev.data.isActive, true);
                        assert.strictEqual(ev.data.optionId, 1);
                    } else {
                        assert.strictEqual(ev.data.itemId, 1);
                        assert.strictEqual(ev.data.isActive, false);
                        assert.strictEqual(ev.data.optionId, false);
                    }
                },
                item_option_changed: function (ev) {
                    if (eventNumber === 1) {
                        assert.strictEqual(ev.data.itemId, 1);
                        assert.strictEqual(ev.data.isActive, true);
                        assert.strictEqual(ev.data.optionId, 2);
                    }
                },
            },
        });
        // open dropdown menu
        dropdownMenu.$('button:first').click();
        // open options menu
        dropdownMenu.$('span.fa-caret-right').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 7);
        // Don't forget there is a hidden li.divider element at first place among children
        assert.ok(!dropdownMenu.$('.o_menu_item:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(3) > .dropdown-item').hasClass('selected'));
        dropdownMenu.$('.o_item_option:first').click();
        assert.ok(dropdownMenu.$('.o_menu_item:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(dropdownMenu.$('.o_item_option:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(3) > .dropdown-item').hasClass('selected'));
        dropdownMenu.$('.o_item_option:nth-child(3)').click();
        assert.ok(dropdownMenu.$('.o_menu_item:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(dropdownMenu.$('.o_item_option:nth-child(3) > .dropdown-item').hasClass('selected'));
        dropdownMenu.$('.o_item_option:nth-child(3)').click();
        assert.ok(!dropdownMenu.$('.o_menu_item:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(2) > .dropdown-item').hasClass('selected'));
        assert.ok(!dropdownMenu.$('.o_item_option:nth-child(3) > .dropdown-item').hasClass('selected'));
        dropdownMenu.destroy();
    });

    QUnit.test('trash an item should be possible', function (assert) {
        assert.expect(3);

        var dropdownMenu = createDropdownMenu(this.dropdownHeader, this.items, {
            intercepts: {
                menu_item_deleted: function (ev) {
                    assert.strictEqual(ev.data.itemId, 2);
                },
            },
        });
        dropdownMenu.$('button:first').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 4);
        dropdownMenu.$('span.o_trash_button').click();
        assert.strictEqual(dropdownMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').length, 2);
        dropdownMenu.destroy();
    });
});
});
