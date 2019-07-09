odoo.define('web.dropdown_menu_tests', function (require) {
"use strict";

var DropdownMenu = require('web.DropdownMenu');
var testUtils = require('web.test_utils');

function createDropdownMenu(items, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new DropdownMenu(null, items);
    testUtils.mock.addMockEnvironment(menu, params);
    return menu.appendTo(target).then(function() {
        return menu;
    });
}

QUnit.module('Web', {
    beforeEach: function () {
        this.items = [
            {
                isActive: false,
                description: 'Some Item',
                id: 1,
                groupId: 1,
                groupNumber: 1,
            },
            {
                isActive: true,
                description: 'Some other Item',
                id: 2,
                groupId: 2,
                groupNumber: 2,
            },
        ];
    },
}, function () {
    QUnit.module('DropdownMenu');

    QUnit.test('simple rendering', async function (assert) {
        assert.expect(4);

        var dropdownMenu = await createDropdownMenu(this.items);
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 4,
            'should have 4 elements counting the dividers');
        assert.strictEqual(dropdownMenu.$('.o_menu_item').first().text().trim(), 'Some Item',
            'first element should have "Some Item" description');
        assert.ok(!dropdownMenu.$('.o_menu_item > .dropdown-item').eq(0).hasClass('selected'),
            'first element should not be selected');
        assert.ok(dropdownMenu.$('.o_menu_item > .dropdown-item').eq(1).hasClass('selected'),
            'second element should be selected');

        dropdownMenu.destroy();
    });

    QUnit.test('click on an item without options should toggle it', async function (assert) {
        assert.expect(7);

        var self = this;
        var dropdownMenu = await createDropdownMenu(this.items, {
            intercepts: {
                menu_item_clicked: function (ev) {
                    assert.strictEqual(ev.data.id, 1);
                    self.items[0].isActive = !self.items[0].isActive;
                    dropdownMenu.update(self.items);
                },
            },
        });
        await testUtils.dom.click(dropdownMenu.$('button:first'));
        assert.doesNotHaveClass(dropdownMenu.$('.o_menu_item:first > .dropdown-item').first(), 'selected');
        await testUtils.dom.click(dropdownMenu.$('.o_menu_item a').first());
        assert.hasClass(dropdownMenu.$('.o_menu_item:first > .dropdown-item'), 'selected');
        assert.ok(dropdownMenu.$('.o_menu_item:first').is(':visible'),
            'item should still be visible');
        await testUtils.dom.click(dropdownMenu.$('.o_menu_item a').first());
        assert.doesNotHaveClass(dropdownMenu.$('.o_menu_item:first > .dropdown-item').first(), 'selected');
        assert.ok(dropdownMenu.$('.o_menu_item:first').is(':visible'),
            'item should still be visible');
        dropdownMenu.destroy();
    });

    QUnit.test('click on an item should not change url', async function (assert) {
        assert.expect(0);

        var dropdownMenu = await createDropdownMenu(this.items);
        await testUtils.dom.click(dropdownMenu.$('.o_dropdown_toggler_btn'));
        dropdownMenu.$el.click(function () {
            // we do not want a click to get out and change the url, for example
            throw new Error('No click should get out of the dropdown menu');
        });
        await testUtils.dom.click(dropdownMenu.$('.o_menu_item a').first());

        dropdownMenu.destroy();
    });

    QUnit.test('options rendering', async function (assert) {
        assert.expect(3);

        this.items[0].hasOptions = true;
        this.items[0].options = [
            {optionId: 1, description: "First Option", groupId: 1},
            {optionId: 2, description: "Second Option", groupId: 1}
        ];
        this.items[0].currentOptionIds = new Set();
        var dropdownMenu = await createDropdownMenu(this.items);
        testUtils.dom.click(dropdownMenu.$('button:first'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 4);
        // open options menu
        await testUtils.dom.click(dropdownMenu.$('span.fa-caret-right'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 7);
        // close options menu
        await testUtils.dom.click(dropdownMenu.$('span.fa-caret-down'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 4);

        dropdownMenu.destroy();
    });

    QUnit.test('close menu closes also submenus', async function (assert) {
        assert.expect(2);

        this.items[0].hasOptions = true;
        this.items[0].options = [
            {optionId: 1, description: "First Option"},
            {optionId: 2, description: "Second Option"}
        ];
        this.items[0].currentOptionIds = new Set();
        var dropdownMenu = await createDropdownMenu(this.items);
        // open dropdown menu
        testUtils.dom.click(dropdownMenu.$('button:first'));
        // open options menu
        await testUtils.dom.click(dropdownMenu.$('span.fa-caret-right'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 7);
        await testUtils.dom.click(dropdownMenu.$('button:first'));
        await testUtils.dom.click(dropdownMenu.$('button:first'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 4);

        dropdownMenu.destroy();
    });

    QUnit.test('click on an option should trigger the event "item_option_clicked" with appropriate data', async function (assert) {
        assert.expect(18);

        var self = this;
        var eventNumber = 0;
        this.items[0].hasOptions = true;
        this.items[0].options = [
            {optionId: 1, description: "First Option"},
            {optionId: 2, description: "Second Option"}
        ];
        this.items[0].currentOptionIds = new Set();
        var dropdownMenu = await createDropdownMenu(this.items, {
            intercepts: {
                item_option_clicked: function (ev) {
                    eventNumber++;
                    assert.strictEqual(ev.data.id, 1);
                    if (eventNumber === 1) {
                        assert.strictEqual(ev.data.optionId, 1);
                        self.items[0].isActive = true;
                        self.items[0].currentOptionIds.add(1);
                    }
                    if (eventNumber === 2) {
                        assert.strictEqual(ev.data.optionId, 2);
                        self.items[0].currentOptionIds = new Set([1,2]);
                    }
                    if (eventNumber === 3) {
                        assert.strictEqual(ev.data.optionId, 1);
                        self.items[0].currentOptionIds = new Set([2]);
                    }
                    if (eventNumber === 4) {
                        assert.strictEqual(ev.data.optionId, 2);
                        self.items[0].isActive = false;
                        self.items[0].currentOptionIds.clear();
                    }
                    dropdownMenu.update(self.items);
                },
            },
        });
        await testUtils.nextTick();
        // open dropdown menu
        await testUtils.dom.click(dropdownMenu.$('button:first'));
        assert.containsN(dropdownMenu, '.dropdown-divider, .o_menu_item', 4);
        await testUtils.dom.clickFirst(dropdownMenu.$('.o_menu_item'));
        // click on first option
        await testUtils.dom.click(dropdownMenu.$('.o_item_option > .dropdown-item').eq(0));
        assert.hasClass(dropdownMenu.$('.o_menu_item > .dropdown-item').first(), 'selected');
        assert.hasClass(dropdownMenu.$('.o_item_option> .dropdown-item').eq(0),'selected');
        assert.doesNotHaveClass(dropdownMenu.$('.o_item_option > .dropdown-item').eq(1), 'selected');
        // click on second option
        await testUtils.dom.click($('.o_item_option > .dropdown-item').eq(1));
        assert.hasClass(dropdownMenu.$('.o_menu_item > .dropdown-item').first(), 'selected');
        assert.hasClass(dropdownMenu.$('.o_item_option > .dropdown-item').eq(0), 'selected');
        assert.hasClass(dropdownMenu.$('.o_item_option > .dropdown-item').eq(1), 'selected');
        // click again on first option
        await testUtils.dom.click(dropdownMenu.$('.o_item_option > .dropdown-item').eq(0));
        // click again on second option
        await testUtils.dom.click($('.o_item_option > .dropdown-item').eq(1));
        assert.doesNotHaveClass(dropdownMenu.$('.o_menu_item > .dropdown-item').first(), 'selected');
        assert.doesNotHaveClass(dropdownMenu.$('.o_item_option > .dropdown-item').eq(0), 'selected');
        assert.doesNotHaveClass(dropdownMenu.$('.o_item_option > .dropdown-item').eq(1), 'selected');

        dropdownMenu.destroy();
    });
});
});
