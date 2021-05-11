/** @odoo-module **/

import {
    makeWithSearch,
    editFavoriteName,
    editSearch,
    getFacetTexts,
    isItemSelected,
    saveFavorite,
    setupControlPanelServiceRegistry,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleMenuItem,
    toggleSaveFavorite,
    validateSearch,
} from "./helpers";
import { patchDate, triggerEvent } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { FavoriteMenu } from "@web/search/favorite_menu/favorite_menu";
import { registry } from "@web/core/registry";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { dialogService } from "@web/core/dialog/dialog_service";

const serviceRegistry = registry.category("services");

/**
 * @param {Component} comp
 */
async function toggleDefaultCheckBox(comp) {
    const checkbox = comp.el.querySelector("input[type='checkbox']");
    checkbox.checked = !checkbox.checked;
    await triggerEvent(checkbox, null, "change");
}

/**
 * @param {Component} comp
 */
async function toggleShareCheckBox(comp) {
    const checkbox = comp.el.querySelectorAll("input[type='checkbox']")[1];
    checkbox.checked = !checkbox.checked;
    await triggerEvent(checkbox, null, "change");
}

function getDomain(comp) {
    return comp.env.searchModel.domain;
}

let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                        float_field: { string: "Float", type: "float", group_operator: "sum" },
                        foo: { string: "Foo", type: "char", store: true, sortable: true },
                    },
                    records: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("CustomFavoriteItem");

    QUnit.test("simple rendering with no favorite", async function (assert) {
        assert.expect(8);

        const controlPanel = await makeWithSearch(
            { serverData },
            {
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
                displayName: "Action Name",
            }
        );

        assert.containsOnce(controlPanel, "div.o_favorite_menu > button i.fa.fa-star");
        assert.strictEqual(
            controlPanel.el
                .querySelector("div.o_favorite_menu > button span")
                .innerText.trim()
                .toUpperCase(),
            "FAVORITES"
        );

        await toggleFavoriteMenu(controlPanel);
        assert.containsNone(controlPanel, ".dropdown-divider");
        assert.containsOnce(controlPanel, ".o_add_favorite");
        assert.strictEqual(
            controlPanel.el.querySelector(".o_add_favorite > button").innerText.trim(),
            "Save current search"
        );

        await toggleSaveFavorite(controlPanel);
        assert.strictEqual(
            controlPanel.el.querySelector('.o_add_favorite input[type="text"]').value,
            "Action Name"
        );
        assert.containsN(
            controlPanel,
            '.o_add_favorite .custom-checkbox input[type="checkbox"]',
            2
        );
        const labelEls = controlPanel.el.querySelectorAll(".o_add_favorite .custom-checkbox label");
        assert.deepEqual(
            [...labelEls].map((e) => e.innerText.trim()),
            ["Use by default", "Share with all users"]
        );
    });

    QUnit.test("favorites use by default and share are exclusive", async function (assert) {
        assert.expect(11);

        const controlPanel = await makeWithSearch(
            { serverData },
            {
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
            }
        );

        await toggleFavoriteMenu(controlPanel);
        await toggleSaveFavorite(controlPanel);
        const checkboxes = controlPanel.el.querySelectorAll('input[type="checkbox"]');

        assert.strictEqual(checkboxes.length, 2, "2 checkboxes are present");

        assert.notOk(checkboxes[0].checked, "Start: None of the checkboxes are checked (1)");
        assert.notOk(checkboxes[1].checked, "Start: None of the checkboxes are checked (2)");

        await toggleDefaultCheckBox(controlPanel);

        assert.ok(checkboxes[0].checked, "The first checkbox is checked");
        assert.notOk(checkboxes[1].checked, "The second checkbox is not checked");

        await toggleShareCheckBox(controlPanel);

        assert.notOk(
            checkboxes[0].checked,
            "Clicking on the second checkbox checks it, and unchecks the first (1)"
        );
        assert.ok(
            checkboxes[1].checked,
            "Clicking on the second checkbox checks it, and unchecks the first (2)"
        );

        await toggleDefaultCheckBox(controlPanel);

        assert.ok(
            checkboxes[0].checked,
            "Clicking on the first checkbox checks it, and unchecks the second (1)"
        );
        assert.notOk(
            checkboxes[1].checked,
            "Clicking on the first checkbox checks it, and unchecks the second (2)"
        );

        await toggleDefaultCheckBox(controlPanel);

        assert.notOk(checkboxes[0].checked, "End: None of the checkboxes are checked (1)");
        assert.notOk(checkboxes[1].checked, "End: None of the checkboxes are checked (2)");
    });

    QUnit.test("save filter", async function (assert) {
        assert.expect(1);

        class TestComponent extends owl.Component {
            setup() {
                useSetupAction({
                    saveParams: () => {
                        return {
                            orderBy: [
                                { asc: true, name: "foo" },
                                { asc: false, name: "bar" },
                            ],
                        };
                    },
                });
            }
        }
        TestComponent.components = { FavoriteMenu };
        TestComponent.template = owl.tags.xml`<div><FavoriteMenu/></div>`;

        const comp = await makeWithSearch(
            {
                serverData,
                mockRPC: (_, args) => {
                    if (args.model === "ir.filters" && args.method === "create_or_replace") {
                        const irFilter = args.args[0];
                        assert.deepEqual(irFilter.sort, '["foo","bar desc"]');
                        return 7; // fake serverSideId
                    }
                },
            },
            {
                resModel: "foo",
                Component: TestComponent,
                searchViewId: false,
            }
        );

        await toggleFavoriteMenu(comp);
        await toggleSaveFavorite(comp);
        await editFavoriteName(comp, "aaa");
        await saveFavorite(comp);
    });

    QUnit.test("dynamic filters are saved dynamic", async function (assert) {
        assert.expect(3);

        const controlPanel = await makeWithSearch(
            {
                serverData,
                mockRPC: (_, args) => {
                    if (args.model === "ir.filters" && args.method === "create_or_replace") {
                        const irFilter = args.args[0];
                        assert.deepEqual(
                            irFilter.domain,
                            '[("date_field", ">=", (context_today() + relativedelta()).strftime("%Y-%m-%d"))]'
                        );
                        return 7; // fake serverSideId
                    }
                },
            },
            {
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Filter" name="filter" domain="[('date_field', '>=', (context_today() + relativedelta()).strftime('%Y-%m-%d'))]"/>
                    </search>
                `,
                context: { search_default_filter: 1 },
            }
        );

        assert.deepEqual(getFacetTexts(controlPanel), ["Filter"]);

        await toggleFavoriteMenu(controlPanel);
        await toggleSaveFavorite(controlPanel);
        await editFavoriteName(controlPanel, "My favorite");
        await saveFavorite(controlPanel);

        assert.deepEqual(getFacetTexts(controlPanel), ["My favorite"]);
    });

    QUnit.test("save filters created via autocompletion works", async function (assert) {
        assert.expect(4);

        const controlPanel = await makeWithSearch(
            {
                serverData,
                mockRPC: (_, args) => {
                    if (args.model === "ir.filters" && args.method === "create_or_replace") {
                        const irFilter = args.args[0];
                        assert.deepEqual(irFilter.domain, '[("foo", "ilike", "a")]');
                        return 7; // fake serverSideId
                    }
                },
            },
            {
                resModel: "foo",
                Component: ControlPanel,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <field name="foo"/>
                    </search>
                `,
            }
        );

        assert.deepEqual(getFacetTexts(controlPanel), []);

        await editSearch(controlPanel, "a");
        await validateSearch(controlPanel);

        assert.deepEqual(getFacetTexts(controlPanel), ["Foo\na"]);

        await toggleFavoriteMenu(controlPanel);
        await toggleSaveFavorite(controlPanel);
        await editFavoriteName(controlPanel, "My favorite");
        await saveFavorite(controlPanel);

        assert.deepEqual(getFacetTexts(controlPanel), ["My favorite"]);
    });

    QUnit.test(
        "default favorite is not activated if activateFavorite is set to false",
        async function (assert) {
            assert.expect(3);

            const controlPanel = await makeWithSearch(
                {
                    serverData,
                },
                {
                    resModel: "foo",
                    Component: ControlPanel,
                    searchMenuTypes: ["favorite"],
                    searchViewId: false,
                    irFilters: [
                        {
                            context: "{}",
                            domain: "[('foo', '=', 'a')]",
                            id: 7,
                            is_default: true,
                            name: "My favorite",
                            sort: "[]",
                            user_id: [2, "Mitchell Admin"],
                        },
                    ],
                    activateFavorite: false,
                }
            );

            await toggleFavoriteMenu(controlPanel);

            assert.notOk(isItemSelected(controlPanel, "My favorite"));
            assert.deepEqual(getDomain(controlPanel), []);
            assert.deepEqual(getFacetTexts(controlPanel), []);
        }
    );

    QUnit.test(
        'toggle favorite correctly clears filter, groupbys, comparison and field "options"',
        async function (assert) {
            assert.expect(11);

            patchDate(2019, 6, 31, 13, 43, 0);

            const controlPanel = await makeWithSearch(
                {
                    serverData,
                },
                {
                    resModel: "foo",
                    Component: ControlPanel,
                    searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
                    searchViewId: false,
                    irFilters: [
                        {
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
                        },
                    ],
                    searchViewArch: `
                        <search>
                            <field string="Foo" name="foo"/>
                            <filter string="Date Field Filter" name="positive" date="date_field" default_period="this_year"/>
                            <filter string="Date Field Groupby" name="coolName" context="{'group_by': 'date_field'}"/>
                        </search>
                    `,
                    context: {
                        search_default_positive: true,
                        search_default_coolName: true,
                        search_default_foo: "a",
                    },
                }
            );

            let domain = controlPanel.env.searchModel.domain;
            let groupBy = controlPanel.env.searchModel.groupBy;
            let comparison = controlPanel.env.searchModel.getComparison();

            assert.deepEqual(domain, [
                "&",
                ["foo", "ilike", "a"],
                "&",
                ["date_field", ">=", "2019-01-01"],
                ["date_field", "<=", "2019-12-31"],
            ]);
            assert.deepEqual(groupBy, ["date_field:month"]);
            assert.deepEqual(comparison, null);

            assert.deepEqual(getFacetTexts(controlPanel), [
                "Foo\na",
                "Date Field Filter: 2019",
                "Date Field Groupby: Month",
            ]);

            // activate a comparison
            await toggleComparisonMenu(controlPanel);
            await toggleMenuItem(controlPanel, "Date Field Filter: Previous Period");

            domain = controlPanel.env.searchModel.domain;
            groupBy = controlPanel.env.searchModel.groupBy;
            comparison = controlPanel.env.searchModel.getComparison();

            assert.deepEqual(domain, [["foo", "ilike", "a"]]);
            assert.deepEqual(groupBy, ["date_field:month"]);
            assert.deepEqual(comparison, {
                comparisonId: "previous_period",
                comparisonRange: [
                    "&",
                    ["date_field", ">=", "2018-01-01"],
                    ["date_field", "<=", "2018-12-31"],
                ],
                comparisonRangeDescription: "2018",
                fieldDescription: "Date Field Filter",
                fieldName: "date_field",
                range: [
                    "&",
                    ["date_field", ">=", "2019-01-01"],
                    ["date_field", "<=", "2019-12-31"],
                ],
                rangeDescription: "2019",
            });

            // activate the unique existing favorite
            await toggleFavoriteMenu(controlPanel);
            await toggleMenuItem(controlPanel, 0);

            domain = controlPanel.env.searchModel.domain;
            groupBy = controlPanel.env.searchModel.groupBy;
            comparison = controlPanel.env.searchModel.getComparison();

            assert.deepEqual(domain, ["!", ["foo", "=", "qsdf"]]);
            assert.deepEqual(groupBy, ["foo"]);
            assert.deepEqual(comparison, {
                "favorite comparison content": "bla bla...",
            });

            assert.deepEqual(getFacetTexts(controlPanel), ["My favorite"]);
        }
    );

    QUnit.test(
        "favorites have unique descriptions (the submenus of the favorite menu are correctly updated)",
        async function (assert) {
            assert.expect(5);

            serviceRegistry.add(
                "notification",
                {
                    start() {
                        return {
                            create(message, options) {
                                assert.strictEqual(
                                    message,
                                    "A filter with same name already exists."
                                );
                                assert.deepEqual(options, { type: "danger" });
                            },
                        };
                    },
                },
                { force: true }
            );

            const controlPanel = await makeWithSearch(
                {
                    serverData,
                    mockRPC: (route, args) => {
                        if (args.model === "ir.filters" && args.method === "create_or_replace") {
                            const irFilter = args.args[0];
                            assert.deepEqual(irFilter, {
                                action_id: false,
                                context: { group_by: [] },
                                domain: "[]",
                                is_default: false,
                                model_id: "foo",
                                name: "My favorite 2",
                                sort: "[]",
                                user_id: 7,
                            });
                            return 2; // serverSideId
                        }
                    },
                },
                {
                    resModel: "foo",
                    Component: ControlPanel,
                    searchMenuTypes: ["favorite"],
                    searchViewId: false,
                    irFilters: [
                        {
                            context: "{}",
                            domain: "[]",
                            id: 1,
                            is_default: false,
                            name: "My favorite",
                            sort: "[]",
                            user_id: [2, "Mitchell Admin"],
                        },
                    ],
                }
            );

            await toggleFavoriteMenu(controlPanel);
            await toggleSaveFavorite(controlPanel);

            // first try: should fail
            await editFavoriteName(controlPanel, "My favorite");
            await saveFavorite(controlPanel);

            // second try: should succeed
            await editFavoriteName(controlPanel, "My favorite 2");
            await saveFavorite(controlPanel);
            await toggleSaveFavorite(controlPanel);

            // third try: should fail
            await editFavoriteName(controlPanel, "My favorite 2");
            await saveFavorite(controlPanel);
        }
    );

    QUnit.skip("save search filter in modal", async function (assert) {
        /** @todo I don't know yet how to convert this test */
        // assert.expect(5);
        // serverData.models = {
        //     partner: {
        //         fields: {
        //             date_field: {
        //                 string: "Date",
        //                 type: "date",
        //                 store: true,
        //                 sortable: true,
        //                 searchable: true,
        //             },
        //             birthday: { string: "Birthday", type: "date", store: true, sortable: true },
        //             foo: { string: "Foo", type: "char", store: true, sortable: true },
        //             bar: { string: "Bar", type: "many2one", relation: "partner" },
        //             float_field: { string: "Float", type: "float", group_operator: "sum" },
        //         },
        //         records: [
        //             {
        //                 id: 1,
        //                 display_name: "First record",
        //                 foo: "yop",
        //                 bar: 2,
        //                 date_field: "2017-01-25",
        //                 birthday: "1983-07-15",
        //                 float_field: 1,
        //             },
        //             {
        //                 id: 2,
        //                 display_name: "Second record",
        //                 foo: "blip",
        //                 bar: 1,
        //                 date_field: "2017-01-24",
        //                 birthday: "1982-06-04",
        //                 float_field: 2,
        //             },
        //             {
        //                 id: 3,
        //                 display_name: "Third record",
        //                 foo: "gnap",
        //                 bar: 1,
        //                 date_field: "2017-01-13",
        //                 birthday: "1985-09-13",
        //                 float_field: 1.618,
        //             },
        //             {
        //                 id: 4,
        //                 display_name: "Fourth record",
        //                 foo: "plop",
        //                 bar: 2,
        //                 date_field: "2017-02-25",
        //                 birthday: "1983-05-05",
        //                 float_field: -1,
        //             },
        //             {
        //                 id: 5,
        //                 display_name: "Fifth record",
        //                 foo: "zoup",
        //                 bar: 2,
        //                 date_field: "2016-01-25",
        //                 birthday: "1800-01-01",
        //                 float_field: 13,
        //             },
        //             { id: 7, display_name: "Partner 6" },
        //             { id: 8, display_name: "Partner 7" },
        //             { id: 9, display_name: "Partner 8" },
        //             { id: 10, display_name: "Partner 9" },
        //         ],
        //     },
        // };
        // const form = await createView({
        //     arch: `
        //     <form string="Partners">
        //         <sheet>
        //             <group>
        //                 <field name="bar"/>
        //             </group>
        //         </sheet>
        //     </form>`,
        //     archs: {
        //         "partner,false,list": '<tree><field name="display_name"/></tree>',
        //         "partner,false,search": '<search><field name="date_field"/></search>',
        //     },
        //     data,
        //     model: "partner",
        //     res_id: 1,
        //     View: FormView,
        //     env: {
        //         dataManager: {
        //             create_filter(filter) {
        //                 assert.strictEqual(
        //                     filter.name,
        //                     "Awesome Test Customer Filter",
        //                     "filter name should be correct"
        //                 );
        //             },
        //         },
        //     },
        // });
        // await testUtils.form.clickEdit(form);
        // await testUtils.fields.many2one.clickOpenDropdown("bar");
        // await testUtils.fields.many2one.clickItem("bar", "Search");
        // assert.containsN(document.body, "tr.o_data_row", 9, "should display 9 records");
        // await toggleFilterMenu(".modal");
        // await toggleAddCustomFilter(".modal");
        // assert.strictEqual(
        //     document.querySelector(".o_filter_condition select.o_generator_menu_field").value,
        //     "date_field",
        //     "date field should be selected"
        // );
        // await applyFilter(".modal");
        // assert.containsNone(document.body, "tr.o_data_row", "should display 0 records");
        // // Save this search
        // await toggleFavoriteMenu(".modal");
        // await toggleSaveFavorite(".modal");
        // const filterNameInput = document.querySelector('.o_add_favorite input[type="text"]');
        // assert.isVisible(filterNameInput, "should display an input field for the filter name");
        // await testUtils.fields.editInput(filterNameInput, "Awesome Test Customer Filter");
        // await click(document.querySelector(".o_add_favorite button.btn-primary"));
        // form.destroy();
    });

    QUnit.skip("modal loads saved search filters", async function (assert) {
        /** @todo I don't know yet how to convert this test */
        // assert.expect(1);
        // const data = {
        //     partner: {
        //         fields: {
        //             bar: { string: "Bar", type: "many2one", relation: "partner" },
        //         },
        //         // 10 records so that the Search button shows
        //         records: Array.apply(null, Array(10)).map(function (_, i) {
        //             return { id: i, display_name: "Record " + i, bar: 1 };
        //         }),
        //     },
        // };
        // const form = await createView({
        //     arch: `
        //     <form string="Partners">
        //         <sheet>
        //             <group>
        //                 <field name="bar"/>
        //             </group>
        //         </sheet>
        //     </form>`,
        //     data,
        //     model: "partner",
        //     res_id: 1,
        //     View: FormView,
        //     interceptsPropagate: {
        //         load_views: function (ev) {
        //             assert.ok(
        //                 ev.data.options.load_filters,
        //                 "opening dialog should load the filters"
        //             );
        //         },
        //     },
        // });
        // await testUtils.form.clickEdit(form);
        // await testUtils.fields.many2one.clickOpenDropdown("bar");
        // await testUtils.fields.many2one.clickItem("bar", "Search");
        // form.destroy();
    });
});
