odoo.define('web.control_panel_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { createControlPanel } = testUtils;

    QUnit.module('ControlPanel', {
        beforeEach() {
            this.fields = {
                display_name: { string: "Displayed name", type: 'char', searchable: true },
                foo: { string: "Foo", type: "char", default: "My little Foo Value", store: true, sortable: true, searchable: true },
                date_field: { string: "Date", type: "date", store: true, sortable: true, searchable: true },
                float_field: { string: "Float", type: "float", searchable: true },
                bar: { string: "Bar", type: "many2one", relation: 'partner', searchable: true },
            };
        }
    }, function () {

        QUnit.test('default field operator', async function (assert) {
            assert.expect(2);

            const fields = {
                foo_op: { string: "Foo Op", type: "char", store: true, sortable: true, searchable: true },
                foo: { string: "Foo", type: "char", store: true, sortable: true, searchable: true },
                bar_op: { string: "Bar Op", type: "many2one", relation: 'partner', searchable: true },
                bar: { string: "Bar", type: "many2one", relation: 'partner', searchable: true },
                selec: { string: "Selec", type: "selection", selection: [['red', "Red"], ['black', "Black"]] },
            };
            const arch = `
                <search>
                    <field name="bar"/>
                    <field name="bar_op" operator="child_of"/>
                    <field name="foo"/>
                    <field name="foo_op" operator="="/>
                    <field name="selec"/>
                </search>`;
            const searchMenuTypes = [];
            const params = {
                cpModelConfig: {
                    arch,
                    fields,
                    context: {
                        show_filterC: true,
                        search_default_bar: 10,
                        search_default_bar_op: 10,
                        search_default_foo: "foo",
                        search_default_foo_op: "foo_op",
                        search_default_selec: 'red',
                    },
                    searchMenuTypes,
                },
                cpProps: { fields, searchMenuTypes },
                env: {
                    session: {
                        async rpc() {
                            return [[10, "Deco Addict"]];
                        },
                    },
                },
            };
            const controlPanel = await createControlPanel(params);

            assert.deepEqual(
                cpHelpers.getFacetTexts(controlPanel).map(t => t.replace(/\s/g, "")),
                [
                    "BarDecoAddict",
                    "BarOpDecoAddict",
                    "Foofoo",
                    "FooOpfoo_op",
                    "SelecRed"
                ]
            );
            assert.deepEqual(
                controlPanel.getQuery().domain,
                [
                    "&", "&", "&", "&",
                    ["bar", "=", 10],
                    ["bar_op", "child_of", 10],
                    ["foo", "ilike", "foo"],
                    ["foo_op", "=", "foo_op"],
                    ["selec", "=", "red"],
                ]
            );
        });

        QUnit.module('Keyboard navigation');

        QUnit.test('remove a facet with backspace', async function (assert) {
            assert.expect(2);

            const params = {
                cpModelConfig: {
                    arch: `<search> <field name="foo"/></search>`,
                    fields: this.fields,
                    context: { search_default_foo: "a" },
                    searchMenuTypes: ['filter'],
                },
                cpProps: { fields: this.fields },
            };

            const controlPanel = await createControlPanel(params);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Foo\na']);

            // delete a facet
            const searchInput = controlPanel.el.querySelector('input.o_searchview_input');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Backspace' });

            assert.containsNone(controlPanel, 'div.o_searchview div.o_searchview_facet');

            // delete nothing (should not crash)
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Backspace' });
        });

        QUnit.test('fields and filters with groups/invisible attribute', async function (assert) {
            // navigation and automatic menu closure don't work here (i don't know why yet) -->
            // should be tested separatly
            assert.expect(16);

            const arch = `
                <search>
                    <field name="display_name" string="Foo B" invisible="1"/>
                    <field name="foo" string="Foo A"/>
                    <filter name="filterA" string="FA" domain="[]"/>
                    <filter name="filterB" string="FB" invisible="1" domain="[]"/>
                    <filter name="filterC" string="FC" invisible="not context.get('show_filterC')" domain="[]"/>
                    <filter name="groupByA" string="GA" context="{ 'group_by': 'date_field:day' }"/>
                    <filter name="groupByB" string="GB" context="{ 'group_by': 'date_field:day' }" invisible="1"/>
                </search>`;
            const searchMenuTypes = ['filter', 'groupBy'];
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    context: {
                        show_filterC: true,
                        search_default_display_name: 'value',
                        search_default_filterB: true,
                        search_default_groupByB: true
                    },
                    searchMenuTypes
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            function selectorContainsValue(selector, value, shouldContain) {
                const elements = [...controlPanel.el.querySelectorAll(selector)];
                const regExp = new RegExp(value);
                const matches = elements.filter(el => regExp.test(el.innerText.replace(/\s/g, "")));
                assert.strictEqual(matches.length, shouldContain ? 1 : 0,
                    `${selector} in the control panel should${shouldContain ? '' : ' not'} contain "${value}".`
                );
            }

            // default filters/fields should be activated even if invisible
            assert.containsN(controlPanel, 'div.o_searchview_facet', 3);
            selectorContainsValue('.o_searchview_facet', "FooBvalue", true);
            selectorContainsValue('.o_searchview_facet .o_facet_values', "FB", true);
            selectorContainsValue('.o_searchview_facet .o_facet_values', "GB", true);

            await cpHelpers.toggleFilterMenu(controlPanel);

            selectorContainsValue('.o_menu_item', "FA", true);
            selectorContainsValue('.o_menu_item', "FB", false);
            selectorContainsValue('.o_menu_item', "FC", true);

            await cpHelpers.toggleGroupByMenu(controlPanel);

            selectorContainsValue('.o_menu_item', "GA", true);
            selectorContainsValue('.o_menu_item', "GB", false);

            // 'a' to filter nothing on bar
            await cpHelpers.editSearch(controlPanel, 'a');

            // the only item in autocomplete menu should be FooA: a
            selectorContainsValue('.o_searchview_autocomplete', "SearchFooAfor:a", true);
            await cpHelpers.validateSearch(controlPanel);
            selectorContainsValue('.o_searchview_facet', "FooAa", true);

            // The items in the Filters menu and the Group By menu should be the same as before
            await cpHelpers.toggleFilterMenu(controlPanel);

            selectorContainsValue('.o_menu_item', "FA", true);
            selectorContainsValue('.o_menu_item', "FB", false);
            selectorContainsValue('.o_menu_item', "FC", true);

            await cpHelpers.toggleGroupByMenu(controlPanel);

            selectorContainsValue('.o_menu_item', "GA", true);
            selectorContainsValue('.o_menu_item', "GB", false);
        });

        QUnit.test('invisible fields and filters with unknown related fields should not be rendered', async function (assert) {
            assert.expect(2);

            // This test case considers that the current user is not a member of
            // the "base.group_system" group and both "bar" and "date_field" fields
            // have field-level access control that limit access to them only from
            // that group.
            //
            // As MockServer currently does not support "groups" access control, we:
            //
            // - emulate field-level access control of fields_get() by removing
            //   "bar" and "date_field" from the model fields
            // - set filters with groups="base.group_system" as `invisible=1` in
            //   view to emulate the behavior of fields_view_get()
            //   [see ir.ui.view `_apply_group()`]

            delete this.fields.bar;
            delete this.fields.date_field;

            const searchMenuTypes = [];
            const params = {
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            assert.containsNone(controlPanel.el, 'div.o_search_options div.o_filter_menu',
                "there should not be filter dropdown");
            assert.containsNone(controlPanel.el, 'div.o_search_options div.o_group_by_menu',
                "there should not be groupby dropdown");
        });

        QUnit.test('groupby menu is not rendered if searchMenuTypes does not have groupBy', async function (assert) {
            assert.expect(2);

            const arch = `<search/>`;
            const searchMenuTypes = ['filter'];
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            assert.containsOnce(controlPanel.el, 'div.o_search_options div.o_filter_menu');
            assert.containsNone(controlPanel.el, 'div.o_search_options div.o_group_by_menu');
        });

        QUnit.test('search field should be autofocused', async function (assert) {
            assert.expect(2);
    
            const controlPanel = await createControlPanel({
                model: 'partner',
                arch: '<search/>',
                data: this.data,
                env: {
                    device: {
                        isMobileDevice: false,
                    },
                },
            });
    
            assert.containsOnce(controlPanel, '.o_searchview_input', "has a search field");
            assert.containsOnce(controlPanel, '.o_searchview_input:focus-within',
                "has autofocused search field");
        });
    
        QUnit.test("search field's autofocus should be disabled on mobile device", async function (assert) {
            assert.expect(2);
    
            const controlPanel = await createControlPanel({
                model: 'partner',
                arch: '<search/>',
                data: this.data,
                env: {
                    device: {
                        isMobileDevice: true,
                    },
                },
            });
    
            assert.containsOnce(controlPanel, '.o_searchview_input', "has a search field");
            assert.containsNone(controlPanel, '.o_searchview_input:focus-within',
                "hasn't autofocused search field");
        });

        QUnit.test("dynamic domains evaluation using global context", async function (assert) {
            const arch = `
                <search>
                    <filter name="filter" domain="[('date_deadline', '&lt;', context.get('my_date'))]"/>
                </search>
            `;
            const context = {
                search_default_filter: true,
                my_date: "2021-09-17",
            };
            const fields = this.fields;
            const searchMenuTypes = ['filter'];
            const controlPanel = await createControlPanel({
                cpModelConfig: { arch, fields, searchMenuTypes, context },
                cpProps: { fields, searchMenuTypes },
            });
            assert.deepEqual(
                controlPanel.getQuery().domain,
                [['date_deadline', '<', "2021-09-17"]]
            );
        });

    });
});
