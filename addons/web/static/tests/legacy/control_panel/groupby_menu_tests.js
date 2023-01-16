odoo.define('web.groupby_menu_tests', function (require) {
    "use strict";

    const { browser } = require('@web/core/browser/browser');
    const { patchWithCleanup } = require('@web/../tests/helpers/utils');
    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { createControlPanel } = testUtils;

    const searchMenuTypes = ['groupBy'];

    QUnit.module('Components', {
        beforeEach: function () {
            this.fields = {
                bar: { string: "Bar", type: "many2one", relation: 'partner' },
                birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                date_field: { string: "Date", type: "date", store: true, sortable: true },
                float_field: { string: "Float", type: "float", group_operator: 'sum' },
                foo: { string: "Foo", type: "char", store: true, sortable: true },
                m2m: { string: "Many2Many", type: "many2many", store: true},
                m2m_not_stored: { string: "Many2Many not stored", type: "many2many" },
            };
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });
        },
    }, function () {

        QUnit.module('GroupByMenu (legacy)');

        QUnit.test('simple rendering with neither groupbys nor groupable fields', async function (assert) {

            assert.expect(1);
            const params = {
                cpModelConfig: { searchMenuTypes },
                cpProps: { fields: {}, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            assert.containsNone(controlPanel, '.o_menu_item, .dropdown-divider, .o_add_custom_group_menu');

            controlPanel.destroy();
        });

        QUnit.test('simple rendering with no groupby', async function (assert) {
            assert.expect(3);

            // Manually make m2m_not_stored to be sortable.
            // Even if it's sortable, it should not be included in the add custom groupby options.
            this.fields.m2m_not_stored.sortable = true;

            const params = {
                cpModelConfig: { searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            assert.containsNone(controlPanel, '.o_menu_item, .dropdown-divider');
            assert.containsOnce(controlPanel, '.o_add_custom_group_menu');

            await cpHelpers.toggleAddCustomGroup(controlPanel);

            const optionEls = controlPanel.el.querySelectorAll('.o_add_custom_group_menu select option');
            assert.deepEqual(
                [...optionEls].map((el) => el.innerText.trim()),
                ['Birthday', 'Date', 'Foo', 'Many2Many']
            );

            controlPanel.destroy();
        });

        QUnit.test('simple rendering with a single groupby', async function (assert) {
            const arch = `
                <search>
                    <filter string="Groupby Foo" name="gb_foo" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: { arch, fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            assert.containsOnce(controlPanel, '.o_menu_item');
            const menuItem = controlPanel.el.querySelector(".o_menu_item");
            assert.strictEqual(menuItem.innerText.trim(), "Groupby Foo");
            assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
            assert.strictEqual(menuItem.ariaChecked, "false");
            assert.containsOnce(controlPanel, '.dropdown-divider');
            assert.containsOnce(controlPanel, '.o_add_custom_group_menu');

            controlPanel.destroy();
        });

        QUnit.test('toggle a "simple" groupby in groupby menu works', async function (assert) {
            assert.expect(13);

            const groupBys = [['foo'], []];
            const arch = `
                <search>
                    <filter string="Groupby Foo" name="gb_foo" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: {arch, fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    const { groupBy } = searchQuery;
                    assert.deepEqual(groupBy, groupBys.shift());
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            assert.notOk(cpHelpers.isItemSelected(controlPanel, 0));
            const menuItem = controlPanel.el.querySelector(".o_menu_item");
            assert.strictEqual(menuItem.innerText.trim(), "Groupby Foo");
            assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
            assert.strictEqual(menuItem.ariaChecked, "false");

            await cpHelpers.toggleMenuItem(controlPanel, 0);
            assert.strictEqual(menuItem.ariaChecked, "true");
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Groupby Foo']);
            assert.containsOnce(controlPanel.el.querySelector('.o_searchview .o_searchview_facet'),
                'span.fa.fa-bars.o_searchview_facet_label');
            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));

            await cpHelpers.toggleMenuItem(controlPanel, 0);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 0));

            controlPanel.destroy();
        });

        QUnit.test('toggle a "simple" groupby quickly does not crash', async function (assert) {
            assert.expect(1);

            const arch = `
                <search>
                    <filter string="Groupby Foo" name="gb_foo" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: { arch, fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);

            cpHelpers.toggleMenuItem(controlPanel, 0);
            cpHelpers.toggleMenuItem(controlPanel, 0);

            assert.ok(true);
            controlPanel.destroy();
        });

        QUnit.test('remove a "Group By" facet properly unchecks groupbys in groupby menu', async function (assert) {
            assert.expect(5);

            const arch = `
                <search>
                    <filter string="Groupby Foo" name="gb_foo" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_gb_foo: 1 }
                },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    const { groupBy } = searchQuery;
                    assert.deepEqual(groupBy, []);
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            const facetEl = controlPanel.el.querySelector('.o_searchview .o_searchview_facet');
            assert.strictEqual(facetEl.innerText.trim(), "Groupby Foo");
            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));

            await testUtils.dom.click(facetEl.querySelector('i.o_facet_remove'));
            assert.containsNone(controlPanel, '.o_searchview .o_searchview_facet');
            await cpHelpers.toggleGroupByMenu(controlPanel);
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 0));

            controlPanel.destroy();
        });

        QUnit.test('group by a date field using interval works', async function (assert) {
            assert.expect(21);

            const groupBys = [
                ['date_field:year', 'date_field:week' ],
                ['date_field:year', 'date_field:month', 'date_field:week'],
                ['date_field:year', 'date_field:month'],
                ['date_field:year'],
                []
            ];

            const arch = `
                <search>
                    <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_date: 1 }
                },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    const { groupBy } = searchQuery;
                    assert.deepEqual(groupBy, groupBys.shift());
                },
            };

            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);

            const optionEls = controlPanel.el.querySelectorAll('span.o_item_option');

            // default groupby should be activated with the  default inteval 'week'
            const { groupBy } = controlPanel.getQuery();
            assert.deepEqual(groupBy, ['date_field:week']);

            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 3));

            // check option descriptions
            const optionDescriptions = [...optionEls].map(e => e.innerText.trim());
            const expectedDescriptions = ['Year', 'Quarter', 'Month', 'Week', 'Day'];
            assert.deepEqual(optionDescriptions, expectedDescriptions);

            const steps = [
                { description: 'Year', facetContent: 'Date: Year>Date: Week', selectedoptions: [0, 3] },
                { description: 'Month', facetContent: 'Date: Year>Date: Month>Date: Week', selectedoptions: [0, 2, 3] },
                { description: 'Week', facetContent: 'Date: Year>Date: Month', selectedoptions: [0, 2] },
                { description: 'Month', facetContent: 'Date: Year', selectedoptions: [0] },
                { description: 'Year', selectedoptions: [] },
            ];
            for (const s of steps) {
                const index = expectedDescriptions.indexOf(s.description);
                await cpHelpers.toggleMenuItemOption(controlPanel, 0, index);
                if (s.facetContent) {
                    assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), [s.facetContent]);
                } else {
                    assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);
                }
                s.selectedoptions.forEach(index => {
                    assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, index));
                });
            }
            controlPanel.destroy();
        });

        QUnit.test('interval options are correctly grouped and ordered', async function (assert) {
            assert.expect(8);

            const arch = `
                <search>
                    <filter string="Bar" name="bar" context="{'group_by': 'bar'}"/>
                    <filter string="Date" name="date" context="{'group_by': 'date_field'}"/>
                    <filter string="Foo" name="foo" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_bar: 1 }
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };

            const controlPanel = await createControlPanel(params);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar']);

            // open menu 'Group By'
            await cpHelpers.toggleGroupByMenu(controlPanel);

            // Open the groupby 'Date'
            await cpHelpers.toggleMenuItem(controlPanel, 'Date');
            // select option 'week'
            await cpHelpers.toggleMenuItemOption(controlPanel, 'Date', 'Week');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar>Date: Week']);

            // select option 'day'
            await cpHelpers.toggleMenuItemOption(controlPanel, 'Date', 'Day');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar>Date: Week>Date: Day']);

            // select option 'year'
            await cpHelpers.toggleMenuItemOption(controlPanel, 'Date', 'Year');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar>Date: Year>Date: Week>Date: Day']);

            // select 'Foo'
            await cpHelpers.toggleMenuItem(controlPanel, 'Foo');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar>Date: Year>Date: Week>Date: Day>Foo']);

            // select option 'quarter'
            await cpHelpers.toggleMenuItem(controlPanel, 'Date');
            await cpHelpers.toggleMenuItemOption(controlPanel, 'Date', 'Quarter');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Bar>Date: Year>Date: Quarter>Date: Week>Date: Day>Foo']);

            // unselect 'Bar'
            await cpHelpers.toggleMenuItem(controlPanel, 'Bar');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Year>Date: Quarter>Date: Week>Date: Day>Foo']);

            // unselect option 'week'
            await cpHelpers.toggleMenuItem(controlPanel, 'Date');
            await cpHelpers.toggleMenuItemOption(controlPanel, 'Date', 'Week');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Year>Date: Quarter>Date: Day>Foo']);

            controlPanel.destroy();
        });

        QUnit.test('the ID field should not be proposed in "Add Custom Group" menu', async function (assert) {
            assert.expect(2);

            const fields = {
                foo: { string: "Foo", type: "char", store: true, sortable: true },
                id: { sortable: true, string: 'ID', type: 'integer' }
            };
            const params = {
                cpModelConfig: { searchMenuTypes },
                cpProps: { fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            await cpHelpers.toggleAddCustomGroup(controlPanel);

            const optionEls = controlPanel.el.querySelectorAll('.o_add_custom_group_menu select option');
            assert.strictEqual(optionEls.length, 1);
            assert.strictEqual(optionEls[0].innerText.trim(), "Foo");

            controlPanel.destroy();
        });

        QUnit.test('add a date field in "Add Custome Group" activate a groupby with global default option "month"', async function (assert) {
            assert.expect(4);

            const fields = {
                date_field: { string: "Date", type: "date", store: true, sortable: true },
                id: { sortable: true, string: 'ID', type: 'integer' }
            };
            const params = {
                cpModelConfig: { fields, searchMenuTypes },
                cpProps: { fields, searchMenuTypes },
                search: function (searchQuery) {
                    const { groupBy } = searchQuery;
                    assert.deepEqual(groupBy, ['date_field:month']);
                }
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            await cpHelpers.toggleAddCustomGroup(controlPanel);
            await cpHelpers.applyGroup(controlPanel);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Month']);

            assert.ok(cpHelpers.isItemSelected(controlPanel, "Date"));
            await cpHelpers.toggleMenuItem(controlPanel, "Date");
            assert.ok(cpHelpers.isOptionSelected(controlPanel, "Date", "Month"));

            controlPanel.destroy();
        });

        QUnit.test('default groupbys can be ordered', async function (assert) {
            assert.expect(2);

            const arch = `
                <search>
                    <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                    <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_birthday: 2, search_default_date: 1 }
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };

            const controlPanel = await createControlPanel(params);

            // the defautl groupbys should be activated in the right order
            const { groupBy } = controlPanel.getQuery();
            assert.deepEqual(groupBy, ['date_field:week', 'birthday:month']);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Week>Birthday: Month']);

            controlPanel.destroy();
        });

        QUnit.test('a separator in groupbys does not cause problems', async function (assert) {
            assert.expect(23);

            const arch = `
                <search>
                    <filter string="Date" name="coolName" context="{'group_by': 'date_field'}"/>
                    <separator/>
                    <filter string="Bar" name="superName" context="{'group_by': 'bar'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };

            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
            await cpHelpers.toggleMenuItemOption(controlPanel, 0, 4);

            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 1));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 4), 'selected');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Day']);

            await cpHelpers.toggleMenuItem(controlPanel, 1);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));
            assert.ok(cpHelpers.isItemSelected(controlPanel, 1));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 4), 'selected');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Day>Bar']);

            await cpHelpers.toggleMenuItemOption(controlPanel, 0, 1);
            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));
            assert.ok(cpHelpers.isItemSelected(controlPanel, 1));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 1), 'selected');
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 4), 'selected');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Quarter>Date: Day>Bar']);

            await cpHelpers.toggleMenuItem(controlPanel, 1);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
            assert.ok(cpHelpers.isItemSelected(controlPanel, 0));
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 1));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 1), 'selected');
            assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, 4), 'selected');
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date: Quarter>Date: Day']);

            await cpHelpers.removeFacet(controlPanel);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            await cpHelpers.toggleGroupByMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 0));
            assert.notOk(cpHelpers.isItemSelected(controlPanel, 1));
            assert.notOk(cpHelpers.isOptionSelected(controlPanel, 0, 1), 'selected');
            assert.notOk(cpHelpers.isOptionSelected(controlPanel, 0, 4), 'selected');

            controlPanel.destroy();
        });

        QUnit.test('falsy search default groupbys are not activated', async function (assert) {
            assert.expect(2);

            const arch = `
                <search>
                    <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                    <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_birthday: false, search_default_foo: 0 }
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };

            const controlPanel = await createControlPanel(params);
            const { groupBy } = controlPanel.getQuery();
            assert.deepEqual(groupBy, []);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            controlPanel.destroy();
        });
    });
});
