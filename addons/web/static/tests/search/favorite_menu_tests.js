/** @odoo-module **/

import { patchDate } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { dialogService } from "@web/core/dialog/dialog_service";
import {
    makeWithSearch,
    getFacetTexts,
    isItemSelected,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleMenuItem,
    setupControlPanelServiceRegistry,
} from "./helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

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

    QUnit.module("FavoriteMenu");

    QUnit.test("simple rendering with no favorite", async function (assert) {
        assert.expect(5);

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
            let comparison = controlPanel.env.searchModel._getComparison();

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
            comparison = controlPanel.env.searchModel._getComparison();

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
            comparison = controlPanel.env.searchModel._getComparison();

            assert.deepEqual(domain, ["!", ["foo", "=", "qsdf"]]);
            assert.deepEqual(groupBy, ["foo"]);
            assert.deepEqual(comparison, {
                "favorite comparison content": "bla bla...",
            });

            assert.deepEqual(getFacetTexts(controlPanel), ["My favorite"]);
        }
    );

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
