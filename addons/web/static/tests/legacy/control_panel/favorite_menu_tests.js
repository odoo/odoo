odoo.define('web.favorite_menu_tests', function (require) {
    "use strict";

    const { browser } = require('@web/core/browser/browser');
    const { patchWithCleanup } = require('@web/../tests/helpers/utils');

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { makeLegacyDialogMappingTestEnv } = require('@web/../tests/helpers/legacy_env_utils');
    const { createControlPanel, createView, mock } = testUtils;
    const { patchDate } = mock;

    const searchMenuTypes = ['favorite'];

    QUnit.module('Components', {
        beforeEach: function () {
            this.fields = {
                bar: { string: "Bar", type: "many2one", relation: 'partner' },
                birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                date_field: { string: "Date", type: "date", store: true, sortable: true },
                float_field: { string: "Float", type: "float", group_operator: 'sum' },
                foo: { string: "Foo", type: "char", store: true, sortable: true },
            };
            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });
        },
    }, function () {

        QUnit.module('FavoriteMenu (legacy)');

        QUnit.test('simple rendering with no favorite', async function (assert) {
            assert.expect(8);

            const params = {
                cpModelConfig: { searchMenuTypes },
                cpProps: { fields: this.fields, searchMenuTypes, action: { name: "Action Name" } },
            };
            const controlPanel = await createControlPanel(params);

            assert.containsOnce(controlPanel, 'div.o_favorite_menu > button i.fa.fa-star');
            assert.strictEqual(controlPanel.el.querySelector('div.o_favorite_menu > button span').innerText.trim(), "Favorites");

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            assert.containsNone(controlPanel, '.dropdown-divider');
            assert.containsOnce(controlPanel, '.o_add_favorite');
            assert.strictEqual(controlPanel.el.querySelector('.o_add_favorite > button').innerText.trim(),
                "Save current search");

            await cpHelpers.toggleSaveFavorite(controlPanel);
            assert.strictEqual(
                controlPanel.el.querySelector('.o_add_favorite input[type="text"]').value,
                'Action Name'
            );
            assert.containsN(controlPanel, '.o_add_favorite .custom-checkbox input[type="checkbox"]', 2);
            const labelEls = controlPanel.el.querySelectorAll('.o_add_favorite .custom-checkbox label');
            assert.deepEqual(
                [...labelEls].map(e => e.innerText.trim()),
                ["Use by default", "Share with all users"]
            );
        });

        QUnit.test('favorites use by default and share are exclusive', async function (assert) {
            assert.expect(11);

            const params = {
                cpModelConfig: {
                    viewInfo: { fields: this.fields },
                    searchMenuTypes
                },
                cpProps: {
                    fields: this.fields,
                    searchMenuTypes,
                    action: {},
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleSaveFavorite(controlPanel);
            const checkboxes = controlPanel.el.querySelectorAll('input[type="checkbox"]');

            assert.strictEqual(checkboxes.length, 2, '2 checkboxes are present');

            assert.notOk(checkboxes[0].checked, 'Start: None of the checkboxes are checked (1)');
            assert.notOk(checkboxes[1].checked, 'Start: None of the checkboxes are checked (2)');

            await testUtils.dom.click(checkboxes[0]);
            assert.ok(checkboxes[0].checked, 'The first checkbox is checked');
            assert.notOk(checkboxes[1].checked, 'The second checkbox is not checked');

            await testUtils.dom.click(checkboxes[1]);
            assert.notOk(checkboxes[0].checked,
                'Clicking on the second checkbox checks it, and unchecks the first (1)');
            assert.ok(checkboxes[1].checked,
                'Clicking on the second checkbox checks it, and unchecks the first (2)');

            await testUtils.dom.click(checkboxes[0]);
            assert.ok(checkboxes[0].checked,
                'Clicking on the first checkbox checks it, and unchecks the second (1)');
            assert.notOk(checkboxes[1].checked,
                'Clicking on the first checkbox checks it, and unchecks the second (2)');

            await testUtils.dom.click(checkboxes[0]);
            assert.notOk(checkboxes[0].checked, 'End: None of the checkboxes are checked (1)');
            assert.notOk(checkboxes[1].checked, 'End: None of the checkboxes are checked (2)');
        });

        QUnit.test('save filter', async function (assert) {
            assert.expect(1);

            const params = {
                cpModelConfig: {
                    fields: this.fields,
                    searchMenuTypes
                },
                cpProps: {
                    fields: this.fields,
                    searchMenuTypes,
                    action: {},
                },
                'get-controller-query-params': function (callback) {
                    callback({
                        orderedBy: [
                            { asc: true, name: 'foo' },
                            { asc: false, name: 'bar' }
                        ]
                    });
                },
                env: {
                    dataManager: {
                        create_filter: async function (filter) {
                            assert.strictEqual(filter.sort, '["foo","bar desc"]',
                                'The right format for the string "sort" should be sent to the server'
                            );
                        }
                    }
                },
            };

            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleSaveFavorite(controlPanel);
            await cpHelpers.editFavoriteName(controlPanel, "aaa");
            await cpHelpers.saveFavorite(controlPanel);
        });

        QUnit.test('dynamic filters are saved dynamic', async function (assert) {
            assert.expect(3);

            const arch = `
            <search>
                <filter string="Float" name="positive" domain="[('date_field', '>=', (context_today() + relativedelta()).strftime('%Y-%m-%d'))]"/>
            </search>
        `;
            const params = {
                cpModelConfig: {
                    fields: {},
                    arch ,
                    searchMenuTypes,
                    context: {
                        search_default_positive: true,
                    }
                },
                cpProps: {
                    fields: {},
                    searchMenuTypes,
                    action: {},
                },
                'get-controller-query-params': function (callback) {
                    callback();
                },
                env: {
                    dataManager: {
                        create_filter: async function (filter) {
                            assert.strictEqual(
                                filter.domain,
                                "[(\"date_field\", \">=\", (context_today() + relativedelta()).strftime(\"%Y-%m-%d\"))]"
                            );
                            return 1; // serverSideId
                        }
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ['Float']);

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleSaveFavorite(controlPanel);
            await cpHelpers.editFavoriteName(controlPanel, "My favorite");
            await cpHelpers.saveFavorite(controlPanel);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["My favorite"]);
        });

        QUnit.test('save filters created via autocompletion works', async function (assert) {
            assert.expect(4);

            const arch = `<search><field name="foo"/></search>`;
            const params = {
                cpModelConfig: {
                    fields: this.fields,
                    arch ,
                    searchMenuTypes,
                },
                cpProps: {
                    fields: this.fields,
                    searchMenuTypes,
                    action: {},
                },
                'get-controller-query-params': function (callback) {
                    callback();
                },
                env: {
                    dataManager: {
                        create_filter: async function (filter) {
                            assert.strictEqual(
                                filter.domain,
                                `[["foo", "ilike", "a"]]`
                            );
                            return 1; // serverSideId
                        }
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);

            await cpHelpers.editSearch(controlPanel, "a");
            await cpHelpers.validateSearch(controlPanel);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["Foo\na"]);

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleSaveFavorite(controlPanel);
            await cpHelpers.editFavoriteName(controlPanel, "My favorite");
            await cpHelpers.saveFavorite(controlPanel);

            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["My favorite"]);
        });

        QUnit.skipWOWL('delete an active favorite remove it both in list of favorite and in search bar', async function (assert) {
            // AAB to discuss with BOI (breaks since we listen to global clicks on capture)
            // in the legacy favorite menu, we open a legacy dialog which doesn't change the ui
            // service active element, so the menu closes itself when we click in the dialog
            // note: where do we still have this menu in prod? (legacy views: no, dashboard: no, studio ?)
            assert.expect(6);

            const favoriteFilters = [{
                context: "{}",
                domain: "[['foo', '=', 'qsdf']]",
                id: 7,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            }];
            const { legacyEnv } = await makeLegacyDialogMappingTestEnv();
            const params = {
                cpModelConfig: { favoriteFilters, searchMenuTypes },
                cpProps: { searchMenuTypes, action: {} },
                search: function (searchQuery) {
                    const { domain } = searchQuery;
                    assert.deepEqual(domain, []);
                },
                env: {
                    ...legacyEnv,
                    dataManager: {
                        delete_filter: function () {
                            return Promise.resolve();
                        }
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFavoriteMenu(controlPanel);

            const { domain } = controlPanel.getQuery();
            assert.deepEqual(domain, [["foo", "=", "qsdf"]]);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), ["My favorite"]);
            assert.hasClass(controlPanel.el.querySelector('.o_favorite_menu .o_menu_item'), 'selected');

            await cpHelpers.deleteFavorite(controlPanel, 0);

            // confirm deletion
            await testUtils.dom.click(document.querySelector('div.o_dialog footer button'));
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);
            const itemEls = controlPanel.el.querySelectorAll('.o_favorite_menu .dropdown-item');
            assert.deepEqual([...itemEls].map(e => e.innerText.trim()), ["Save current search"]);
        });

        QUnit.test('default favorite is not activated if key search_disable_custom_filters is set to true', async function (assert) {
            assert.expect(2);

            const favoriteFilters = [{
                context: "{}",
                domain: "",
                id: 7,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            }];
            const params = {
                cpModelConfig: {
                    favoriteFilters,
                    searchMenuTypes,
                    context: { search_disable_custom_filters: true }
                },
                cpProps: { searchMenuTypes, action: {} },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFavoriteMenu(controlPanel);

            const { domain } = controlPanel.getQuery();
            assert.deepEqual(domain, []);
            assert.deepEqual(cpHelpers.getFacetTexts(controlPanel), []);
        });

        QUnit.test('toggle favorite correctly clears filter, groupbys, comparison and field "options"', async function (assert) {
            assert.expect(11);

            const unpatchDate = patchDate(2019, 6, 31, 13, 43, 0);

            const favoriteFilters = [{
                context: `
                    {
                        "group_by": ["foo"],
                        "comparison": {
                            "favorite comparison content": "bla bla..."
                        },
                    }
                `,
                domain: "['!', ['foo', '=', 'qsdf']]",
                id: 7,
                is_default: false,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            }];
            let firstSearch = true;
            const arch = `
            <search>
                <field string="Foo" name="foo"/>
                <filter string="Date Field Filter" name="positive" date="date_field" default_period="this_year"/>
                <filter string="Date Field Groupby" name="coolName" context="{'group_by': 'date_field'}"/>
            </search>
        `;
            const searchMenuTypes = ['filter', 'groupBy', 'comparison', 'favorite'];
            const params = {
                cpModelConfig: {
                    favoriteFilters,
                    arch,
                    fields: this.fields,
                    searchMenuTypes,
                    context: {
                        search_default_positive: true,
                        search_default_coolName: true,
                        search_default_foo: "a",
                    }
                },
                cpProps: { searchMenuTypes, action: {}, fields: this.fields },
                search: function (searchQuery) {
                    const { domain, groupBy, timeRanges } = searchQuery;
                    if (firstSearch) {
                        assert.deepEqual(domain, [['foo', 'ilike', 'a']]);
                        assert.deepEqual(groupBy, ['date_field:month']);
                        assert.deepEqual(timeRanges, {
                            comparisonId: "previous_period",
                            comparisonRange: ["&", ["date_field", ">=", "2018-01-01"], ["date_field", "<=", "2018-12-31"]],
                            comparisonRangeDescription: "2018",
                            fieldDescription: "Date Field Filter",
                            fieldName: "date_field",
                            range: ["&", ["date_field", ">=", "2019-01-01"], ["date_field", "<=", "2019-12-31"]],
                            rangeDescription: "2019",
                        });
                        firstSearch = false;
                    } else {
                        assert.deepEqual(domain, ['!', ['foo', '=', 'qsdf']]);
                        assert.deepEqual(groupBy, ['foo']);
                        assert.deepEqual(timeRanges, {
                            "favorite comparison content": "bla bla...",
                            range: undefined,
                            comparisonRange: undefined,
                        });
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            const { domain, groupBy, timeRanges } = controlPanel.getQuery();
            assert.deepEqual(domain, [
                "&",
                ["foo", "ilike", "a"],
                "&",
                ["date_field", ">=", "2019-01-01"],
                ["date_field", "<=", "2019-12-31"]
            ]);
            assert.deepEqual(groupBy, ['date_field:month']);
            assert.deepEqual(timeRanges, {});

            assert.deepEqual(
                cpHelpers.getFacetTexts(controlPanel),
                [
                    'Foo\na',
                    'Date Field Filter: 2019',
                    'Date Field Groupby: Month',
                ]
                );

            // activate a comparison
            await cpHelpers.toggleComparisonMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, "Date Field Filter: Previous period");

            // activate the unique existing favorite
            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleMenuItem(controlPanel, 0);

            assert.deepEqual(
                cpHelpers.getFacetTexts(controlPanel),
                ["My favorite"]
            );

            unpatchDate();
        });

        QUnit.test('favorites have unique descriptions (the submenus of the favorite menu are correctly updated)', async function (assert) {
            assert.expect(3);

            const favoriteFilters = [{
                context: "{}",
                domain: "[]",
                id: 1,
                is_default: false,
                name: "My favorite",
                sort: "[]",
                user_id: [2, "Mitchell Admin"],
            }];
            const params = {
                cpModelConfig: { favoriteFilters, searchMenuTypes },
                cpProps: { searchMenuTypes, action: {} },
                'get-controller-query-params': function (callback) {
                    callback();
                },
                env: {
                    session: { uid: 4 },
                    services: {
                        notification: {
                            notify: function (params) {
                                assert.deepEqual(params, {
                                    message: "Filter with same name already exists.",
                                    type: "danger"
                                });
                            },
                        }
                    },
                    dataManager: {
                        create_filter: async function (irFilter) {
                            assert.deepEqual(irFilter, {
                                "action_id": undefined,
                                "context": { "group_by": [] },
                                "domain": "[]",
                                "is_default": false,
                                "model_id": undefined,
                                "name": "My favorite 2",
                                "sort": "[]",
                                "user_id": 4,
                            });
                            return 2; // serverSideId
                        }
                    }
                },
            };
            const controlPanel = await createControlPanel(params);

            await cpHelpers.toggleFavoriteMenu(controlPanel);
            await cpHelpers.toggleSaveFavorite(controlPanel);

            // first try: should fail
            await cpHelpers.editFavoriteName(controlPanel, "My favorite");
            await cpHelpers.saveFavorite(controlPanel);

            // second try: should succeed
            await cpHelpers.editFavoriteName(controlPanel, "My favorite 2");
            await cpHelpers.saveFavorite(controlPanel);

            // third try: should fail
            await cpHelpers.editFavoriteName(controlPanel, "My favorite 2");
            await cpHelpers.saveFavorite(controlPanel);
        });

        QUnit.test('save search filter in modal', async function (assert) {
            assert.expect(5);
            const data = {
                partner: {
                    fields: {
                        date_field: { string: "Date", type: "date", store: true, sortable: true, searchable: true },
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        foo: { string: "Foo", type: "char", store: true, sortable: true },
                        bar: { string: "Bar", type: "many2one", relation: 'partner' },
                        float_field: { string: "Float", type: "float", group_operator: 'sum' },
                    },
                    records: [
                        { id: 1, display_name: "First record", foo: "yop", bar: 2, date_field: "2017-01-25", birthday: "1983-07-15", float_field: 1 },
                        { id: 2, display_name: "Second record", foo: "blip", bar: 1, date_field: "2017-01-24", birthday: "1982-06-04", float_field: 2 },
                        { id: 3, display_name: "Third record", foo: "gnap", bar: 1, date_field: "2017-01-13", birthday: "1985-09-13", float_field: 1.618 },
                        { id: 4, display_name: "Fourth record", foo: "plop", bar: 2, date_field: "2017-02-25", birthday: "1983-05-05", float_field: -1 },
                        { id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, date_field: "2016-01-25", birthday: "1800-01-01", float_field: 13 },
                        { id: 7, display_name: "Partner 6", },
                        { id: 8, display_name: "Partner 7", },
                        { id: 9, display_name: "Partner 8", },
                        { id: 10, display_name: "Partner 9", }
                    ],
                },
            };
            const form = await createView({
                arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="bar"/>
                        </group>
                    </sheet>
                </form>`,
                archs: {
                    'partner,false,list': '<tree><field name="display_name"/></tree>',
                    'partner,false,search': '<search><field name="date_field"/></search>',
                },
                data,
                model: 'partner',
                res_id: 1,
                View: FormView,
                env: {
                    dataManager: {
                        create_filter(filter) {
                            assert.strictEqual(filter.name, "Awesome Test Customer Filter",
                                "filter name should be correct");
                        },
                    }
                },
            });

            await testUtils.form.clickEdit(form);

            await testUtils.fields.many2one.clickOpenDropdown('bar');
            await testUtils.fields.many2one.clickItem('bar', 'Search');

            assert.containsN(document.body, 'tr.o_data_row', 9, "should display 9 records");

            const modal = document.body.querySelector(".modal");
            await cpHelpers.toggleFilterMenu(modal);
            await cpHelpers.toggleAddCustomFilter(modal);
            assert.strictEqual(document.querySelector('.o_filter_condition select.o_generator_menu_field').value,
                'date_field',
                "date field should be selected");
            await cpHelpers.applyFilter(modal);

            assert.containsNone(document.body, 'tr.o_data_row', "should display 0 records");

            // Save this search
            await cpHelpers.toggleFavoriteMenu(modal);
            await cpHelpers.toggleSaveFavorite(modal);

            const filterNameInput = document.querySelector('.o_add_favorite input[type="text"]');
            assert.isVisible(filterNameInput, "should display an input field for the filter name");

            await testUtils.fields.editInput(filterNameInput, 'Awesome Test Customer Filter');
            await testUtils.dom.click(document.querySelector('.o_add_favorite button.btn-primary'));

            form.destroy();
        });

        QUnit.test('modal loads saved search filters', async function (assert) {
            assert.expect(1);
            const data = {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: 'partner' },
                    },
                    // 10 records so that the Search button shows
                    records: Array.apply(null, Array(10)).map(function(_, i) {
                        return { id: i, display_name: "Record " + i, bar: 1 };
                    })
                },
            };
            const form = await createView({
                arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="bar"/>
                        </group>
                    </sheet>
                </form>`,
                data,
                model: 'partner',
                res_id: 1,
                View: FormView,
                interceptsPropagate: {
                    load_views: function (ev) {
                        assert.ok(ev.data.options.load_filters, "opening dialog should load the filters");
                    },
                },
            });

            await testUtils.form.clickEdit(form);

            await testUtils.fields.many2one.clickOpenDropdown('bar');
            await testUtils.fields.many2one.clickItem('bar', 'Search');

            form.destroy();
        });
    });
});
