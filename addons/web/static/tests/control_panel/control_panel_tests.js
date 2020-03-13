odoo.define('web.control_panel_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');

    const cpHelpers = testUtils.controlPanel;
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

        QUnit.module('Keyboard navigation');

        QUnit.test('remove a facet with backspace', async function (assert) {
            assert.expect(2);

            const params = {
                cpStoreConfig: {
                    viewInfo: {
                        arch: `<search> <field name="foo"/></search>`,
                        fields: this.fields,
                    },
                    actionContext: { search_default_foo: "a" },
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

            controlPanel.destroy();
        });

        QUnit.test('fields and filters with groups/invisible attribute', async function (assert) {
            // navigation and automatic menu closure don't work here (i don't know why yet) -->
            // should be tested separatly
            assert.expect(14);

            const arch = `
                <search>
                    <field name="display_name" string="Foo B" invisible="1"/>
                    <field name="foo" string="Foo A"/>
                    <filter name="filterA" string="FA" domain="[]"/>
                    <filter name="filterB" string="FB" invisible="1" domain="[]"/>
                    <filter name="groupByA" string="GA" context="{ 'group_by': 'date_field:day' }"/>
                    <filter name="groupByB" string="GB" context="{ 'group_by': 'date_field:day' }" invisible="1"/>
                </search>`;
            const searchMenuTypes = ['filter', 'groupBy'];
            const params = {
                cpStoreConfig: {
                    viewInfo: { arch, fields: this.fields },
                    actionContext: {
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

            selectorContainsValue('.o_menu_item a', "FA", true);
            selectorContainsValue('.o_menu_item a', "FB", false);

            await cpHelpers.toggleGroupByMenu(controlPanel);

            selectorContainsValue('.o_menu_item a', "GA", true);
            selectorContainsValue('.o_menu_item a', "GB", false);

            // 'a' to filter nothing on bar
            await cpHelpers.editSearch(controlPanel, 'a');

            // the only item in autocomplete menu should be FooA: a
            selectorContainsValue('.o_searchview_autocomplete', "SearchFooAfor:a", true);
            await cpHelpers.validateSearch(controlPanel);
            selectorContainsValue('.o_searchview_facet', "FooAa", true);

            // The items in the Filters menu and the Group By menu should be the same as before
            await cpHelpers.toggleFilterMenu(controlPanel);

            selectorContainsValue('.o_menu_item a', "FA", true);
            selectorContainsValue('.o_menu_item a', "FB", false);

            await cpHelpers.toggleGroupByMenu(controlPanel);

            selectorContainsValue('.o_menu_item a', "GA", true);
            selectorContainsValue('.o_menu_item a', "GB", false);

            controlPanel.destroy();
        });
    });
});
