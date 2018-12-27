odoo.define('web.search_groupby_menu_tests', function (require) {
"use strict";

var GroupByMenu = require('web.GroupByMenu');
var testUtils = require('web.test_utils');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var INTERVAL_OPTIONS = controlPanelViewParameters.INTERVAL_OPTIONS;

function createGroupByMenu(groupBys, fields, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new GroupByMenu(null, groupBys, fields);
    testUtils.mock.addMockEnvironment(menu, params);
    menu.appendTo(target);
    return menu;
}

QUnit.module('GroupByMenu', {
    beforeEach: function () {
        this.groupBys = [
            {
                description: 'some group by',
                groupNumber: 1,
                isActive: false,
            },
        ];
        this.fields = {
            fieldName: {sortable: true, string: 'Super Date', type: 'date'}
        };
    },
}, function () {

    QUnit.test('simple rendering with no filter and no field', function (assert) {
        assert.expect(1);

        var groupByMenu = createGroupByMenu([], {});
        // open groupBy menu
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.containsNone(groupByMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text',
            'should have 0 element');

        groupByMenu.destroy();
    });

    QUnit.test('simple rendering', function (assert) {
        assert.expect(2);

        var groupByMenu = createGroupByMenu(this.groupBys, this.fields);
        // open groupBy menu
        testUtils.dom.click(groupByMenu.$('button:first'));
        groupByMenu.$('button:first').click();
        assert.containsN(groupByMenu, '.dropdown-divider, .dropdown-item', 4);
        assert.strictEqual(groupByMenu.$('.o_menu_item').text().trim(), 'some group by',
            'should have proper filter name');

        groupByMenu.destroy();
    });

    QUnit.test('simple rendering with no filter but fields', function (assert) {
        assert.expect(1);

        var groupByMenu = createGroupByMenu(
            [],
            {fieldName: {sortable: true, string: 'Super Date', type: 'date'}}
            );
        testUtils.dom.click(groupByMenu.$('button:first'));
        assert.containsOnce(groupByMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 'should have 1 element');

        groupByMenu.destroy();
    });

    QUnit.test('click on add custom group toggle group selector', function (assert) {
        assert.expect(2);

        var groupByMenu = createGroupByMenu([],
            {fieldName: {sortable: true, string: 'Super Date', type: 'date'}}
        );
        testUtils.dom.click(groupByMenu.$('button:first'));
        var selector = groupByMenu.$('select.o_group_selector');
        assert.ok(!selector.is(":visible"), 'should be invisible');
        testUtils.dom.click(groupByMenu.$('.o_add_custom_group'));
        selector = groupByMenu.$('select.o_group_selector');
        assert.ok(selector.is(":visible"), 'should be visible');

        groupByMenu.destroy();
    });

    QUnit.test('select a groupBy of no date type in Add Custom Group menu add properly that groupBy to menu', function (assert) {
        assert.expect(6);

        var groupByMenu = createGroupByMenu(
            [],
            {
                fieldName: {sortable: true, name: 'candlelight', string: 'Candlelight', type: 'boolean'},
            },
            {
                intercepts: {
                    new_groupBy: function (ev) {
                        assert.strictEqual(ev.data.description, 'Candlelight');
                        assert.strictEqual(ev.data.fieldName, 'fieldName');
                        assert.strictEqual(ev.data.fieldType, 'boolean');
                        assert.strictEqual(ev.data.type, 'groupBy');
                        groupByMenu.update([{
                            description: 'Candlelight',
                            groupNumber: 1,
                            isActive: true,
                        }]);
                    },
                },
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

    QUnit.test('select a groupBy of date type in Add Custom Group menu add properly that groupBy to menu', function (assert) {
        assert.expect(13);

        INTERVAL_OPTIONS = INTERVAL_OPTIONS.map(function (option) {
            return _.extend(option, {description: option.description.toString()});
        });

        var groupByMenu = createGroupByMenu(
            [],
            this.fields,
            {
                intercepts: {
                    new_groupBy: function (ev) {
                        assert.strictEqual(ev.data.description, 'Super Date');
                        assert.strictEqual(ev.data.fieldName, 'fieldName');
                        assert.strictEqual(ev.data.fieldType, 'date');
                        assert.strictEqual(ev.data.type, 'groupBy');
                        assert.strictEqual(ev.data.hasOptions, true);
                        assert.deepEqual(ev.data.options, controlPanelViewParameters.INTERVAL_OPTIONS);
                        assert.strictEqual(ev.data.defaultOptionId, controlPanelViewParameters.DEFAULT_INTERVAL);
                        assert.strictEqual(ev.data.currentOptionId, false);
                        groupByMenu.update([{
                            description: 'Super Date',
                            fieldName: 'fieldName',
                            groupNumber: 1,
                            isActive: true,
                            hasOptions: true,
                            options: controlPanelViewParameters.INTERVAL_OPTIONS,
                            currentOptionId: controlPanelViewParameters.DEFAULT_INTERVAL,
                        }]);
                    },
                },
            }
        );
        // open groupBy menu
        testUtils.dom.click(groupByMenu.$('button:first'));
        // open Add Custom Group submenu
        testUtils.dom.click(groupByMenu.$('.o_add_custom_group'));
        // select fieldName
        assert.strictEqual(groupByMenu.$('select').val(), 'fieldName',
            'the select value should be "fieldName"');
        // create new groupBy of type date
        groupByMenu.$('button.o_apply_group').click();
        assert.strictEqual(groupByMenu.$('.o_menu_item > .dropdown-item.selected').length, 1,
            'there should be a groupby selected');
        assert.strictEqual(groupByMenu.$('.o_menu_item .o_submenu_switcher').length, 1,
            'there should be options available');
        // open options submenu
        groupByMenu.$('.o_menu_item .o_submenu_switcher').click();
        assert.strictEqual(groupByMenu.$('.o_item_option').length, 5,
            'there should be five options available');
        assert.strictEqual(groupByMenu.$('.o_add_custom_group').length, 0,
            'there should be no more a Add Custome Group submenu');

        groupByMenu.destroy();
    });
});
});
