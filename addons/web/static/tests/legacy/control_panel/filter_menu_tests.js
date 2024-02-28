odoo.define('web.filter_menu_tests', function (require) {
    "use strict";

    const { browser } = require('@web/core/browser/browser');
    const { patchWithCleanup } = require('@web/../tests/helpers/utils');
    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { createControlPanel, mock } = testUtils;
    const { patchDate } = mock;

    const searchMenuTypes = ['filter'];

    QUnit.module('Components', {
        beforeEach: function () {
            this.fields = {
                date_field: { string: "Date", type: "date", store: true, sortable: true, searchable: true },
                foo: { string: "Foo", type: "char", store: true, sortable: true },
            };
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });
        },
    }, function () {

        QUnit.module('FilterMenu (legacy)');

        QUnit.test('simple rendering with no filter', async function (assert) {
            assert.expect(2);

            const params = {
                cpModelConfig: { searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            assert.containsNone(controlPanel, '.o_menu_item, .dropdown-divider');
            assert.containsOnce(controlPanel, '.o_add_custom_filter_menu');
        });

        QUnit.test('simple rendering with a single filter', async function (assert) {
            const arch = `
                <search>
                    <filter string="Foo" name="foo" domain="[]"/>
                </search>`;
            const params = {
                cpModelConfig: { arch, fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            assert.containsOnce(controlPanel, '.o_menu_item');
            assert.containsOnce(controlPanel, ".o_menu_item[role=menuitemcheckbox]");
            assert.deepEqual(controlPanel.el.querySelector(".o_menu_item").ariaChecked, "false");
            assert.containsOnce(controlPanel, '.dropdown-divider');
            assert.containsOnce(controlPanel, 'div.o_add_custom_filter_menu');
        });

        QUnit.test('should have Date and ID field proposed in that order in "Add custom Filter" submenu', async function (assert) {
            assert.expect(2);

            const params = {
                cpModelConfig: { fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleAddCustomFilter(controlPanel);
            const optionEls = controlPanel.el.querySelectorAll('.o_filter_condition select.o_generator_menu_field option');
            assert.strictEqual(optionEls[0].innerText.trim(), 'Date');
            assert.strictEqual(optionEls[1].innerText.trim(), 'ID');
        });

        QUnit.test('toggle a "simple" filter in filter menu works', async function (assert) {
            assert.expect(12);

            const domains = [
                [['foo', '=', 'qsdf']],
                []
            ];
            const arch = `
                <search>
                    <filter string="Foo" name="foo" domain="[['foo', '=', 'qsdf']]"/>
                </search>`;
            const params = {
                cpModelConfig: { arch, searchMenuTypes },
                cpProps: { fields: {}, searchMenuTypes },
                search: function (searchQuery) {
                    const { domain } = searchQuery;
                    assert.deepEqual(domain, domains.shift());
                }
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            assert.notOk(cpHelpers.isItemSelected(controlPanel, 0));
            assert.containsOnce(controlPanel, ".o_menu_item[role=menuitemcheckbox]");
            assert.deepEqual(controlPanel.el.querySelector(".o_menu_item").ariaChecked, "false");
            await cpHelpers.toggleMenuItem(controlPanel, "Foo");
            assert.deepEqual(controlPanel.el.querySelector(".o_menu_item").ariaChecked, "true");

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Foo']);
            assert.containsOnce(controlPanel.el.querySelector('.o_searchview .o_searchview_facet'),
                'span.fa.fa-filter.o_searchview_facet_label');

            assert.ok(cpHelpers.isItemSelected(controlPanel, "Foo"));

            await cpHelpers.toggleMenuItem(controlPanel, "Foo");
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);
            assert.notOk(cpHelpers.isItemSelected(controlPanel, "Foo"));
        });

        QUnit.test('add a custom filter works', async function (assert) {
            assert.expect(1);

            const params = {
                cpModelConfig: { fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleAddCustomFilter(controlPanel);
            // choose ID field in 'Add Custome filter' menu and value 1
            await cpHelpers.editConditionField(controlPanel, 0, 'id');
            await cpHelpers.editConditionValue(controlPanel, 0, 1);
            await cpHelpers.applyFilter(controlPanel);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['ID is "1"']);
        });

        QUnit.test('deactivate a new custom filter works', async function (assert) {
            assert.expect(4);

            const unpatchDate = patchDate(2020, 1, 5, 12, 20, 0);

            const params = {
                cpModelConfig: { fields: this.fields, searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleAddCustomFilter(controlPanel);
            await cpHelpers.applyFilter(controlPanel);

            assert.ok(cpHelpers.isItemSelected(controlPanel, 'Date is equal to "02/05/2020"'));
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Date is equal to "02/05/2020"']);

            await cpHelpers.toggleMenuItem(controlPanel, 'Date is equal to "02/05/2020"');

            assert.notOk(cpHelpers.isItemSelected(controlPanel, 'Date is equal to "02/05/2020"'));
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            unpatchDate();
        });

        QUnit.test('filter by a date field using period works', async function (assert) {
            assert.expect(56);

            const unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

            const basicDomains = [
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]],
                ["&", ["date_field", ">=", "2017-02-01"], ["date_field", "<=", "2017-02-28"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-01-31"]],
                ["|",
                    "&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-01-31"],
                    "&", ["date_field", ">=", "2017-10-01"], ["date_field", "<=", "2017-12-31"]
                ],
                ["&", ["date_field", ">=", "2017-10-01"], ["date_field", "<=", "2017-12-31"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-03-31"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]],
                ["&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]],
                ["|",
                    "&", ["date_field", ">=", "2016-01-01"], ["date_field", "<=", "2016-12-31"],
                    "&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]
                ],
                ["|",
                    "|",
                        "&", ["date_field", ">=", "2015-01-01"], ["date_field", "<=", "2015-12-31"],
                        "&", ["date_field", ">=", "2016-01-01"], ["date_field", "<=", "2016-12-31"],
                        "&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"]
                ],
                ["|",
                    "|",
                        "&", ["date_field", ">=", "2015-03-01"], ["date_field", "<=", "2015-03-31"],
                        "&", ["date_field", ">=", "2016-03-01"], ["date_field", "<=", "2016-03-31"],
                        "&", ["date_field", ">=", "2017-03-01"], ["date_field", "<=", "2017-03-31"]
                ]
            ];

            const arch = `
                <search>
                    <filter string="Date" name="date_field" date="date_field"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_date_field: 1 },
                },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    // we inspect query domain
                    const { domain } = searchQuery;
                    if (domain.length) {
                        assert.deepEqual(domain, basicDomains.shift());
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, "Date");

            const optionEls = controlPanel.el.querySelectorAll('span.o_item_option');

            // default filter should be activated with the global default period 'this_month'
            const { domain } = controlPanel.getQuery();
            assert.deepEqual(
                domain,
                ["&", ["date_field", ">=", "2017-03-01"], ["date_field", "<=", "2017-03-31"]]
            );
            assert.ok(cpHelpers.isItemSelected(controlPanel, "Date"));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, "Date", 0));

            // check option descriptions
            const optionDescriptions = [...optionEls].map(e => e.innerText.trim());
            const expectedDescriptions = [
                'March', 'February', 'January',
                'Q4', 'Q3', 'Q2', 'Q1',
                '2017', '2016', '2015'
            ];
            assert.deepEqual(optionDescriptions, expectedDescriptions);

            // check generated domains
            const steps = [
                { description: 'March', facetContent: 'Date: 2017', selectedoptions: [7] },
                { description: 'February', facetContent: 'Date: February 2017', selectedoptions: [1, 7] },
                { description: 'February', facetContent: 'Date: 2017', selectedoptions: [7] },
                { description: 'January', facetContent: 'Date: January 2017', selectedoptions: [2, 7] },
                { description: 'Q4', facetContent: 'Date: January 2017/Q4 2017', selectedoptions: [2, 3, 7] },
                { description: 'January', facetContent: 'Date: Q4 2017', selectedoptions: [3, 7] },
                { description: 'Q4', facetContent: 'Date: 2017', selectedoptions: [7] },
                { description: 'Q1', facetContent: 'Date: Q1 2017', selectedoptions: [6, 7] },
                { description: 'Q1', facetContent: 'Date: 2017', selectedoptions: [7] },
                { description: '2017', selectedoptions: [] },
                { description: '2017', facetContent: 'Date: 2017', selectedoptions: [7] },
                { description: '2016', facetContent: 'Date: 2016/2017', selectedoptions: [7, 8] },
                { description: '2015', facetContent: 'Date: 2015/2016/2017', selectedoptions: [7, 8, 9] },
                { description: 'March', facetContent: 'Date: March 2015/March 2016/March 2017', selectedoptions: [0, 7, 8, 9] }
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
                    assert.ok(cpHelpers.isOptionSelected(controlPanel, 0, index),
                        `at step ${steps.indexOf(s) + 1}, option ${expectedDescriptions[index]} should be selected`);
                });
            }

            unpatchDate();
        });

        QUnit.test('filter by a date field using period works even in January', async function (assert) {
            assert.expect(5);

            const unpatchDate = patchDate(2017, 0, 7, 3, 0, 0);

            const arch = `
                <search>
                    <filter string="Date" name="some_filter" date="date_field" default_period="last_month"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: { search_default_some_filter: 1 },
                },
                cpProps: { fields: this.fields, searchMenuTypes },
            };
            const controlPanel = await createControlPanel(params);

            const { domain } = controlPanel.getQuery();
            assert.deepEqual(domain, [
                '&',
                ["date_field", ">=", "2016-12-01"],
                ["date_field", "<=", "2016-12-31"]
            ]);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["Date: December 2016"]);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, "Date");

            assert.ok(cpHelpers.isItemSelected(controlPanel, "Date"));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, "Date", 'December'));
            assert.ok(cpHelpers.isOptionSelected(controlPanel, "Date", '2016'));

            unpatchDate();
        });

        QUnit.test('`context` key in <filter> is used', async function (assert) {
            assert.expect(1);

            const arch = `
                <search>
                    <filter string="Filter" name="some_filter" domain="[]" context="{'coucou_1': 1}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes
                },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    // we inspect query context
                    const { context } = searchQuery;
                    assert.deepEqual(context, { coucou_1: 1 });
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
        });

        QUnit.test('Filter with JSON-parsable domain works', async function (assert) {
            assert.expect(1);

            const originalDomain = [['foo', '=', 'Gently Weeps']];
            const xml_domain = JSON.stringify(originalDomain);

            const arch =
                `<search>
                    <filter string="Foo" name="gently_weeps" domain="${_.escape(xml_domain)}"/>
                </search>`;
            const params = {
                cpModelConfig: {
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                },
                cpProps: { fields: this.fields, searchMenuTypes },
                search: function (searchQuery) {
                    const { domain } = searchQuery;
                    assert.deepEqual(domain, originalDomain,
                        'A JSON parsable xml domain should be handled just like any other'
                    );
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);
        });

        QUnit.test('filter with date attribute set as search_default', async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2019, 6, 31, 13, 43, 0);

            const arch =
                `<search>
                    <filter string="Date" name="date_field" date="date_field" default_period="last_month"/>
                </search>`,
                params = {
                    cpModelConfig: {
                        arch,
                        fields: this.fields,
                        searchMenuTypes,
                        context: {
                            search_default_date_field: true
                        }
                    },
                    cpProps: { fields: this.fields, searchMenuTypes },
                };
            const controlPanel = await createControlPanel(params);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["Date: June 2019"]);

            unpatchDate();
        });

        QUnit.test('filter domains are correcly combined by OR and AND', async function (assert) {
            assert.expect(2);

            const arch =
                `<search>
                    <filter string="Filter Group 1" name="f_1_g1" domain="[['foo', '=', 'f1_g1']]"/>
                    <separator/>
                    <filter string="Filter 1 Group 2" name="f1_g2" domain="[['foo', '=', 'f1_g2']]"/>
                    <filter string="Filter 2 GROUP 2" name="f2_g2" domain="[['foo', '=', 'f2_g2']]"/>
                </search>`,
                params = {
                    cpModelConfig: {
                        arch,
                        fields: this.fields,
                        searchMenuTypes,
                        context: {
                            search_default_f_1_g1: true,
                            search_default_f1_g2: true,
                            search_default_f2_g2: true,
                        }
                    },
                    cpProps: { fields: this.fields, searchMenuTypes },
                };
            const controlPanel = await createControlPanel(params);

            const { domain } = controlPanel.getQuery();
            assert.deepEqual(domain, [
                '&',
                ['foo', '=', 'f1_g1'],
                '|',
                ['foo', '=', 'f1_g2'],
                ['foo', '=', 'f2_g2']
            ]);

            assert.deepEqual(
                cpHelpers.getFacetTexts(controlPanel),
                ["Filter Group 1", "Filter 1 Group 2orFilter 2 GROUP 2"]
            );
        });

        QUnit.test('arch order of groups of filters preserved', async function (assert) {
            assert.expect(12);

            const arch =
                `<search>
                    <filter string="1" name="coolName1" date="date_field"/>
                    <separator/>
                    <filter string="2" name="coolName2" date="date_field"/>
                    <separator/>
                    <filter string="3" name="coolName3" domain="[]"/>
                    <separator/>
                    <filter string="4" name="coolName4" domain="[]"/>
                    <separator/>
                    <filter string="5" name="coolName5" domain="[]"/>
                    <separator/>
                    <filter string="6" name="coolName6" domain="[]"/>
                    <separator/>
                    <filter string="7" name="coolName7" domain="[]"/>
                    <separator/>
                    <filter string="8" name="coolName8" domain="[]"/>
                    <separator/>
                    <filter string="9" name="coolName9" domain="[]"/>
                    <separator/>
                    <filter string="10" name="coolName10" domain="[]"/>
                    <separator/>
                    <filter string="11" name="coolName11" domain="[]"/>
                </search>`,
                params = {
                    cpModelConfig: {
                        arch,
                        fields: this.fields,
                        searchMenuTypes,
                    },
                    cpProps: { fields: this.fields, searchMenuTypes },
                };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFilterMenu(controlPanel);
            assert.containsN(controlPanel, '.o_filter_menu .o_menu_item', 11);

            const menuItemEls = controlPanel.el.querySelectorAll('.o_filter_menu .o_menu_item');
            [...menuItemEls].forEach((e, index) => {
                assert.strictEqual(e.innerText.trim(), String(index + 1));
            });
        });
    });
});
