odoo.define('web.search_filters_menu_tests', function (require) {
"use strict";

var Domain = require('web.Domain');
var FilterMenu = require('web.FilterMenu');
var pyUtils = require('web.py_utils');
var testUtils = require('web.test_utils');

function createFilterMenu(filters, fields, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new FilterMenu(null, filters, fields);
    testUtils.mock.addMockEnvironment(menu, params);
    return menu.appendTo(target).then(function() {
        return menu;
    });
}

QUnit.module('FilterMenu', {
    beforeEach: function () {
        this.filters = [
            {
                isActive: false,
                description: 'some filter',
                domain: '',
                groupNumber: 1,
            },
        ];
        this.fields = {
            boolean_field: {string: "Boolean Field", type: "boolean", default: true, searchable: true},
            date_field: {string: "A date", type: "date", searchable: true},
            char_field: {string: "Char Field", type: "char", default: "foo", searchable: true, trim: true},
        };
    },
}, function () {

    QUnit.test('simple rendering with no filter', async function (assert) {
        assert.expect(3);

        var filterMenu = await createFilterMenu([], this.fields);
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        assert.containsNone(filterMenu, '.dropdown-divider');
        assert.containsNone(filterMenu, '.o_add_filter_menu');
        assert.containsOnce(filterMenu, '.o_add_custom_filter',
            'should have one element: a add custom filter item');
        filterMenu.destroy();
    });

    QUnit.test('simple rendering with a filter', async function (assert) {
        assert.expect(2);

        var filterMenu = await createFilterMenu(this.filters, this.fields);
        assert.containsN(filterMenu, '.dropdown-divider, .dropdown-item, .o_add_custom_filter', 4,
            'should have 4 elements: a hidden separator, a filter, a separator, a add custom filter item');
        assert.containsOnce(filterMenu, '.o_add_custom_filter');
        filterMenu.destroy();
    });

    QUnit.test('click on add custom filter opens the submenu', async function (assert) {
        assert.expect(3);

        var filterMenu = await createFilterMenu([], this.fields);
        // open menu dropdown
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        // open add custom filter submenu
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        assert.containsNone(filterMenu, '.dropdown-divider');
        assert.isVisible(filterMenu.$('.o_add_filter_menu'));
        assert.containsN(filterMenu, '.dropdown-item, .dropdown-item-text', 3,
            'should have 3 elements: a add custom filter item, a proposition, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('removing last prop disable the apply button', async function (assert) {
        assert.expect(2);

        var filterMenu = await createFilterMenu([], this.fields);
        // open menu dropdown and custom filter submenu
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));

        // remove the current unique proposition
        await testUtils.dom.click(filterMenu.$('.o_searchview_extended_delete_prop'));

        assert.containsNone(filterMenu, '.dropdown-divider');
        assert.containsN(filterMenu, '.dropdown-item, .dropdown-item-text', 2,
            'should have 2 elements: a add custom filter item, a apply button + add condition button');

        filterMenu.destroy();
    });

    QUnit.test('readding a proposition reenable apply button', async function (assert) {
        assert.expect(1);

        var filterMenu = await createFilterMenu([], this.fields);
        // open menu dropdown and custom filter submenu, remove existing prop
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.dom.click(filterMenu.$('.o_searchview_extended_delete_prop'));
        // read a proposition
        await testUtils.dom.click(filterMenu.$('.o_add_condition'));
        assert.ok(!filterMenu.$('.o_apply_filter').attr('disabled'));

        filterMenu.destroy();
    });

    QUnit.test('adding a simple filter works', async function (assert) {
        assert.expect(6);

        delete this.fields.date_field;
        var filterMenu = await createFilterMenu([], this.fields, {
            intercepts: {
                new_filters: function (ev) {
                    var filter = ev.data.filters[0];
                    assert.strictEqual(filter.type, 'filter');
                    assert.strictEqual(filter.description, 'Boolean Field is true');
                    assert.strictEqual(filter.domain, '[[\"boolean_field\",\"=\",True]]');
                    filterMenu.update([{
                        isActive: true,
                        description: '?',
                        domain: '?',
                        groupNumber: 1,
                    }]);
                },
            },
        });
        // open menu dropdown and custom filter submenu, remove existing prop
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        // click on apply to activate filter
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));
        assert.containsNone(filterMenu, '.o_filter_condition');
        assert.containsN(filterMenu, '.dropdown-divider', 2);
        assert.isNotVisible(filterMenu.$('.dropdown-divider').eq(0));
        filterMenu.destroy();
    });

    QUnit.test('commit search with an extended proposition with field char does not cause a crash', async function (assert) {
        assert.expect(6);

        this.fields = {many2one_field: {string: "Trululu", type: "many2one", relation: 'partner', selectable: true, searchable: true}};

        var expectedDomains = [
            [['many2one_field','ilike', `a`]],
            [['many2one_field','ilike', `"a"`]],
            [['many2one_field','ilike', `'a'`]],
            [['many2one_field','ilike', `'`]],
            [['many2one_field','ilike', `"`]],
            [['many2one_field','ilike', `\\`]],
        ];

        var filterMenu = await createFilterMenu([], this.fields, {
            intercepts: {
                new_filters: function (ev) {
                    var filter = ev.data.filters[0];
                    // this step combine a tokenization/parsing followed by a string formatting
                    var domain = pyUtils.assembleDomains([filter.domain]);
                    domain = Domain.prototype.stringToArray(domain);
                    assert.deepEqual(domain, expectedDomains.shift());
                },
            }
        });

        // open menu dropdown and custom filter submenu, select trululu field and enter string `a`, then click apply
        await testUtils.dom.click(filterMenu.$('span.fa-filter'));
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `a`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));


        // open custom filter submenu, select trululu field and enter string `"a"`, then click apply
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `"a"`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        // open custom filter submenu, select trululu field and enter string `'a'`, then click apply
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `'a'`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        // open custom filter submenu, select trululu field and enter string `'`, then click apply
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `'`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        // open custom filter submenu, select trululu field and enter string `"`, then click apply
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `"`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        // open custom filter submenu, select trululu field and enter string `\`, then click apply
        await testUtils.dom.click(filterMenu.$('.o_add_custom_filter'));
        await testUtils.fields.editSelect(filterMenu.$('.o_filter_condition select.o_input.o_searchview_extended_prop_field'), 'many2one_field');
        await testUtils.fields.editInput(filterMenu.$('.o_filter_condition .o_searchview_extended_prop_value input'), `\\`);
        await testUtils.dom.click(filterMenu.$('.o_apply_filter'));

        filterMenu.destroy();
    });
});
});
