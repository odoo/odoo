odoo.define('web.search_groupby_menu_tests', function (require) {
"use strict";

var GroupByMenu = require('web.GroupByMenu');
var testUtils = require('web.test_utils');

function createGroupByMenu(groupbys, fields, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new GroupByMenu(null, groupbys, fields);
    testUtils.mock.addMockEnvironment(menu, params);
    menu.appendTo(target);
    return menu;
}

QUnit.module('GroupByMenu', {
    beforeEach: function () {
        this.groupbys = [
            {
                isActive: false,
                description: 'some group by',
                fieldName: 'fieldname',
                itemId: 'red',
                groupId: 1,
            },
        ];
        this.fields = {
            fieldname: {sortable: true, string: 'Super Date', type: 'date', isDate: true}
        };
    },
}, function () {

    QUnit.test('simple rendering', function (assert) {
        assert.expect(2);

        var groupByMenu = createGroupByMenu(this.groupbys, this.fields);
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.containsN(groupByMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 2, 'should have 2 elements');
        assert.strictEqual(groupByMenu.$('.dropdown-divider, .dropdown-item, .dropdown-item-text').eq(1).text().trim(), 'some group by',
            'should have proper filter name');
        groupByMenu.destroy();
    });

    QUnit.test('simple rendering with no filter and no field', function (assert) {
        assert.expect(1);

        var groupByMenu = createGroupByMenu([], {});
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.containsNone(groupByMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 'should have 0 element');
        groupByMenu.destroy();
    });

    QUnit.test('simple rendering with no filter but fields', function (assert) {
        assert.expect(1);

        var groupByMenu = createGroupByMenu(
            [],
            {fieldname: {sortable: true, string: 'Super Date', type: 'date', isDate: true}}
            );
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.containsOnce(groupByMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 'should have 1 element');
        groupByMenu.destroy();
    });

    QUnit.test('click on add custom group toggle group selector', function (assert) {
        assert.expect(2);

        var groupByMenu = createGroupByMenu([], {fieldname: {sortable: true, string: 'Super Date', type: 'date', isDate: true}});
        testUtils.dom.click(groupByMenu.$('button:first'));
        var selector = groupByMenu.$('select.o_group_selector');
        assert.ok(!selector.is(":visible"), 'should be invisible');
        testUtils.dom.click(groupByMenu.$('.o_add_custom_group'));
        selector = groupByMenu.$('select.o_group_selector');
        assert.ok(selector.is(":visible"), 'should be visible');
        groupByMenu.destroy();
    });

    QUnit.test('select a group using the group selector add properly add that group to menu', function (assert) {
        assert.expect(2);

        var groupByMenu = createGroupByMenu(
            [],
            {
                fieldName: {sortable: true, name: 'candlelight', string: 'Candlelight', type: 'boolean'},
            }
        );
        testUtils.dom.click(groupByMenu.$('button:first'));
        testUtils.dom.click(groupByMenu.$('.o_add_custom_group'));
        assert.strictEqual(groupByMenu.$('select').val(), 'fieldName',
            'the select value should be "fieldName"');
        testUtils.dom.click(groupByMenu.$('button.o_apply_group'));
        assert.containsOnce(groupByMenu, '.o_menu_item > .dropdown-item.selected', 'there should be a groupby selected');
        groupByMenu.destroy();
    });

    QUnit.test('click on a groupby filter (not of date type) should activate it', function (assert) {
        assert.expect(5);

        this.groupbys = [{
            isActive: false,
            description: 'another group by',
            fieldName: 'float_field',
            itemId: 'green',
            groupId: 1,
        }];
        this.fields = {float_field: {sortable: true, string: 'Super Float', type: 'float'}};

        var groupByMenu = createGroupByMenu(this.groupbys, this.fields, {
            intercepts: {
                menu_item_toggled: function (ev) {
                    assert.strictEqual(ev.data.itemId, 'green');
                    assert.strictEqual(ev.data.isActive, true);
                },
            },
        });
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.doesNotHaveClass(groupByMenu.$('.o_menu_item:first > .dropdown-item'), 'selected');
        testUtils.dom.click(groupByMenu.$('.o_menu_item a').first());
        assert.hasClass(groupByMenu.$('.o_menu_item:first > .dropdown-item'), 'selected');
        assert.ok(groupByMenu.$('.o_menu_item:first').is(':visible'),
            'group by filter should still be visible');
        groupByMenu.destroy();
    });

    QUnit.test('click on a groupby filter of date type should open menu option', function (assert) {
        assert.expect(4);

        var groupByMenu = createGroupByMenu(this.groupbys,
            {fieldname: {sortable: true, string: 'Super Date', type: 'date', isDate: true}});
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.doesNotHaveClass(groupByMenu.$('.o_menu_item:first > .dropdown-item'), 'selected');
        testUtils.dom.click(groupByMenu.$('.o_menu_item a').first());
        assert.doesNotHaveClass(groupByMenu.$('.o_menu_item:first > .dropdown-item'), 'selected');
        assert.ok(groupByMenu.$('.o_menu_item:first').is(':visible'),
            'group by filter should still be visible');
        assert.ok(groupByMenu.$('.o_item_option').length, 5);
        groupByMenu.destroy();
    });

    QUnit.test('click on groupby filter should not change url', function (assert) {
        assert.expect(0);

        var groupByMenu = createGroupByMenu(this.groupbys,
            {fieldname: {sortable: true, string: 'Super Date', type: 'date', isDate: true}}
        );
        testUtils.dom.click(groupByMenu.$('.o_dropdown_toggler_btn'));
        groupByMenu.$el.click(function (event) {
            // we do not want a click to get out and change the url, for example
            throw new Error('No click should get out of the groupby menu');
        });
        testUtils.dom.click(groupByMenu.$('.o_menu_item a').first());

        groupByMenu.destroy();
    });
});
});
