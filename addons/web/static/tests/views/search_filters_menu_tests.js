odoo.define('web.search_filters_menu_tests', function (require) {
"use strict";

var FiltersMenu = require('web.FiltersMenu');
var testUtils = require('web.test_utils');

function createFiltersMenu(filters, fields, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new FiltersMenu(null, filters, fields);
    testUtils.mock.addMockEnvironment(menu, params);
    menu.appendTo(target);
    return menu;
}

QUnit.module('FiltersMenu', {
    beforeEach: function () {
        this.filters = [
            {
                isActive: false,
                description: 'some filter',
                domain: '',
                name: 'red',
                groupId: 1,
            },
        ];
        this.fields = {
            boolean_field: {string: "Boolean Field", type: "boolean", default: true, searchable: true},
            date_field: {string: "A date", type: "date", searchable: true},
            char_field: {string: "Char Field", type: "char", default: "foo", searchable: true, trim: true},
        };
    },
}, function () {

    QUnit.test('simple rendering with no filter', function (assert) {
        assert.expect(4);

        var filterMenu = createFiltersMenu([], this.fields);
        testUtils.dom.click(filterMenu.$('span.fa-filter'));
        assert.containsOnce(filterMenu, '.dropdown-divider');
        assert.ok(!filterMenu.$('.dropdown-divider').is(':visible'));
        assert.containsN(filterMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 3,
            'should have 3 elements: a hidden divider, a add custom filter item, a apply button + add condition button');
        assert.containsOnce(filterMenu, '.o_add_custom_filter.o_closed_menu');
        filterMenu.destroy();
    });

    QUnit.test('simple rendering with a filter', function (assert) {
        assert.expect(2);

        var filterMenu = createFiltersMenu(this.filters, this.fields);
        assert.containsN(filterMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 5,
            'should have 4 elements: a hidden, separator, a filter, a separator, a add custom filter item, a apply button + add condition button');
        assert.containsOnce(filterMenu, '.o_add_custom_filter.o_closed_menu');
        filterMenu.destroy();
    });

    QUnit.test('click on add custom filter opens the submenu', function (assert) {
        assert.expect(3);

        var filterMenu = createFiltersMenu([], this.fields);
        // open menu dropdown
        testUtils.dom.click(filterMenu.$('span.fa-filter'));
        // open add custom filter submenu
        testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        assert.hasClass(filterMenu.$('.o_add_custom_filter'), 'o_open_menu');
        assert.ok(filterMenu.$('.o_add_filter_menu').is(':visible'));
        assert.containsN(filterMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 4,
            'should have 3 elements: a hidden divider, a add custom filter item, a proposition, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('removing last prop disable the apply button', function (assert) {
        assert.expect(2);

        var filterMenu = createFiltersMenu([], this.fields);
        // open menu dropdown and custom filter submenu
        testUtils.dom.click(filterMenu.$('span.fa-filter'));
        testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));

        // remove the current unique proposition
        testUtils.dom.click(filterMenu.$('.o_searchview_extended_delete_prop'));

        assert.ok(filterMenu.$('.o_apply_filter').attr('disabled'));

        assert.containsN(filterMenu, '.dropdown-divider, .dropdown-item, .dropdown-item-text', 3,
            'should have 3 elements: a hidden separator, a add custom filter item, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('readding a proposition reenable apply button', function (assert) {
        assert.expect(1);

        var filterMenu = createFiltersMenu([], this.fields);

        // open menu dropdown and custom filter submenu, remove existing prop
        testUtils.dom.click(filterMenu.$('span.fa-filter'));
        testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        testUtils.dom.click(filterMenu.$('.o_searchview_extended_delete_prop'));

        // read a proposition
        testUtils.dom.click(filterMenu.$('.o_add_condition'));

        assert.ok(!filterMenu.$('.o_apply_filter').attr('disabled'));

        filterMenu.destroy();
    });

    QUnit.test('adding a simple filter works', function (assert) {
        assert.expect(3);
        delete this.fields.date_field;

        var filterMenu = createFiltersMenu([], this.fields);

        // open menu dropdown and custom filter submenu, remove existing prop
        testUtils.dom.click(filterMenu.$('span.fa-filter'));
        testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));

        // click on apply to activate filter
        testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        assert.hasClass(filterMenu.$('.o_add_custom_filter'), 'o_closed_menu');
        assert.containsNone(filterMenu, '.o_filter_condition');
        assert.containsOnce(filterMenu, '.dropdown-divider:visible',
            'there should be a separator between filters and add custom filter menu');

        filterMenu.destroy();
    });

    QUnit.test('adding a date filter', function (assert) {
        assert.expect(5);
        var filters = [{
                itemId: 1,
                isActive: false,
                description: 'some filter',
                isPeriod: true,
                name: 'Filter Date',
                fieldName: 'date_field',
                groupId: 1,
            },
        ];

        var filterMenu = createFiltersMenu(filters, this.fields, {
            intercepts: {
                menu_item_toggled: function (ev) {
                    assert.strictEqual(ev.data.optionId, 'this_quarter',
                        "should trigger event with proper period");
                },
            },
        });

        // open menu dropdown
        testUtils.dom.click(filterMenu.$('span.fa-filter'));

        assert.containsNone(filterMenu, '.o_menu_item ul',
            "there should not be a sub menu item list");

        // open date sub menu
        testUtils.dom.click(filterMenu.$('.o_submenu_switcher'));
        assert.containsOnce(filterMenu, '.o_menu_item ul',
            "there should be a sub menu item list");

        // click on This Quarter option
        assert.doesNotHaveClass(filterMenu.$('.o_menu_item li[data-option_id="this_quarter"] .dropdown-item'), 'selected',
            "menu item should not be selected");
        testUtils.dom.click(filterMenu.$('.o_menu_item li[data-option_id="this_quarter"] a'));
        assert.hasClass(filterMenu.$('.o_menu_item li[data-option_id="this_quarter"] .dropdown-item'),'selected',
            "menu item should be selected");

        filterMenu.destroy();
    });
});
});
