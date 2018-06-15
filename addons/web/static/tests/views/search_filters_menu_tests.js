odoo.define('web.search_filters_menu_tests', function (require) {
"use strict";

var FiltersMenu = require('web.FiltersMenu');
var testUtils = require('web.test_utils');

function createFiltersMenu(filters, fields, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new FiltersMenu(null, filters, fields);
    testUtils.addMockEnvironment(menu, params);
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
        filterMenu.$('span.fa-filter').click();
        assert.strictEqual(filterMenu.$('.divider').length, 1);
        assert.ok(!filterMenu.$('.divider').is(':visible'));
        assert.strictEqual(filterMenu.$('li').length, 3,
            'should have 3 li: a hidden divider, a add custom filter item, a apply button + add condition button');
        assert.strictEqual(filterMenu.$('li.o_add_custom_filter.o_closed_menu').length, 1);
        filterMenu.destroy();
    });

    QUnit.test('simple rendering with a filter', function (assert) {
        assert.expect(2);

        var filterMenu = createFiltersMenu(this.filters, this.fields);
        assert.strictEqual(filterMenu.$('li').length, 5,
            'should have 4 li: a hidden, separator, a filter, a separator, a add custom filter item, a apply button + add condition button');
        assert.strictEqual(filterMenu.$('li.o_add_custom_filter.o_closed_menu').length, 1);
        filterMenu.destroy();
    });

    QUnit.test('click on add custom filter opens the submenu', function (assert) {
        assert.expect(3);

        var filterMenu = createFiltersMenu([], this.fields);
        // open menu dropdown
        filterMenu.$('span.fa-filter').click();
        // open add custom filter submenu
        filterMenu.$('li.o_add_custom_filter').click();
        assert.ok(filterMenu.$('li.o_add_custom_filter').hasClass('o_open_menu'));
        assert.ok(filterMenu.$('li.o_add_filter_menu').is(':visible'));
        assert.strictEqual(filterMenu.$('li').length, 4,
            'should have 3 li: a hidden divider, a add custom filter item, a proposition, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('removing last prop disable the apply button', function (assert) {
        assert.expect(2);

        var filterMenu = createFiltersMenu([], this.fields);
        // open menu dropdown and custom filter submenu
        filterMenu.$('span.fa-filter').click();
        filterMenu.$('li.o_add_custom_filter').click();

        // remove the current unique proposition
        filterMenu.$('.o_searchview_extended_delete_prop').click();

        assert.ok(filterMenu.$('.o_apply_filter').attr('disabled'));

        assert.strictEqual(filterMenu.$('li').length, 3,
            'should have 3 li: a hidden separator, a add custom filter item, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('readding a proposition reenable apply button', function (assert) {
        assert.expect(1);

        var filterMenu = createFiltersMenu([], this.fields);

        // open menu dropdown and custom filter submenu, remove existing prop
        filterMenu.$('span.fa-filter').click();
        filterMenu.$('li.o_add_custom_filter').click();
        filterMenu.$('.o_searchview_extended_delete_prop').click();

        // read a proposition
        filterMenu.$('.o_add_condition').click();

        assert.ok(!filterMenu.$('.o_apply_filter').attr('disabled'));

        filterMenu.destroy();
    });

    QUnit.test('adding a simple filter works', function (assert) {
        assert.expect(3);
        delete this.fields.date_field;

        var filterMenu = createFiltersMenu([], this.fields);

        // open menu dropdown and custom filter submenu, remove existing prop
        filterMenu.$('span.fa-filter').click();
        filterMenu.$('li.o_add_custom_filter').click();

        // click on apply to activate filter
        filterMenu.$('.o_apply_filter').click();

        assert.ok(filterMenu.$('.o_add_custom_filter').hasClass('o_closed_menu'));
        assert.strictEqual(filterMenu.$('.o_filter_condition').length, 0);
        assert.strictEqual(filterMenu.$('.divider:visible').length, 1,
            'there should be a separator between filters and add custom filter menu');

        filterMenu.destroy();
    });



});
});
