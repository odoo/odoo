/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    patchDate,
    patchWithCleanup,
    nextTick,
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import {
    getFacetTexts,
    makeWithSearch,
    removeFacet,
    setupControlPanelServiceRegistry,
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    deleteFavorite,
    isItemSelected,
    isOptionSelected,
    openAddCustomFilterDialog,
    setupControlPanelFavoriteMenuRegistry,
} from "./helpers";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { registry } from "@web/core/registry";
import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import { createWebClient, doAction } from "../webclient/helpers";
import { openModelFieldSelectorPopover } from "@web/../tests/core/model_field_selector_tests";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";

function getDomain(searchable) {
    return searchable.env.searchModel.domain;
}

function getContext(searchable) {
    return searchable.env.searchModel.context;
}

const viewRegistry = registry.category("views");
const favoriteMenuRegistry = registry.category("favoriteMenu");

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        foo: { string: "Foo", type: "char", store: true, sortable: true },
                        birthday: {
                            string: "Birthday",
                            type: "date",
                            store: true,
                            sortable: true,
                        },
                        date_field: {
                            string: "Date",
                            type: "date",
                            store: true,
                            sortable: true,
                        },
                        properties: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "parent_id",
                            definition_record_field: "properties_definition",
                            name: "properties",
                        },
                        parent_id: {
                            string: "Parent",
                            type: "many2one",
                            relation: "parentModel",
                            name: "parent_id",
                        },
                    },
                },
                parentModel: {
                    fields: {
                        properties_definition: { type: "properties_definition" },
                    },
                },
            },
            views: {
                "foo,false,search": `
                    <search>
                        <filter name="birthday" date="birthday"/>
                        <filter name="date_field" date="date_field"/>
                    </search>`,
            },
        };
        setupControlPanelServiceRegistry();
        setupControlPanelFavoriteMenuRegistry();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
    });

    QUnit.module("SearchBarMenu", () => {
        QUnit.module("Comparison");
        QUnit.test("simple rendering", async function (assert) {
            patchDate(1997, 0, 9, 12, 0, 0);
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["filter", "comparison"],
                searchViewId: false,
            });
            assert.containsOnce(target, ".o_searchview_dropdown_toggler");
            assert.containsNone(target, ".dropdown.o_comparison_menu");
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Birthday");
            await toggleMenuItemOption(target, "Birthday", "January");
            assert.containsOnce(target, ".o_comparison_menu .fa.fa-adjust");
            assert.strictEqual(
                target
                    .querySelector(".o_comparison_menu .o_dropdown_title")
                    .innerText.trim()
                    .toUpperCase(),
                "COMPARISON"
            );
            assert.containsN(target, ".o_comparison_menu .dropdown-item", 2);
            assert.containsN(target, ".o_comparison_menu .dropdown-item[role=menuitemcheckbox]", 2);
            const comparisonOptions = [
                ...target.querySelectorAll(".o_comparison_menu .dropdown-item"),
            ];
            assert.deepEqual(
                comparisonOptions.map((e) => e.innerText.trim()),
                ["Birthday: Previous Period", "Birthday: Previous Year"]
            );
            assert.deepEqual(
                comparisonOptions.map((e) => e.ariaChecked),
                ["false", "false"]
            );
        });

        QUnit.test("activate a comparison works", async function (assert) {
            patchDate(1997, 0, 9, 12, 0, 0);
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter", "comparison"],
                searchViewId: false,
            });
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Birthday");
            await toggleMenuItemOption(target, "Birthday", "January");
            await toggleMenuItem(target, "Birthday: Previous Period");
            assert.deepEqual(getFacetTexts(target), [
                "Birthday: January 1997",
                "Birthday: Previous Period",
            ]);
            await toggleMenuItem(target, "Date");
            await toggleMenuItemOption(target, "Date", "December");
            await toggleMenuItem(target, "Date: Previous Year");
            assert.deepEqual(getFacetTexts(target), [
                ["Birthday: January 1997", "Date: December 1996"].join("\nor\n"),
                "Date: Previous Year",
            ]);
            await toggleMenuItemOption(target, "Date", "1996");
            assert.deepEqual(getFacetTexts(target), ["Birthday: January 1997"]);
            await toggleMenuItem(target, "Birthday: Previous Year");
            assert.containsN(target, ".o_comparison_menu .dropdown-item", 2);
            assert.containsN(target, ".o_comparison_menu .dropdown-item[role=menuitemcheckbox]", 2);
            const comparisonOptions = [
                ...target.querySelectorAll(".o_comparison_menu .dropdown-item"),
            ];
            assert.deepEqual(
                comparisonOptions.map((e) => e.innerText.trim()),
                ["Birthday: Previous Period", "Birthday: Previous Year"]
            );
            assert.deepEqual(
                comparisonOptions.map((e) => e.ariaChecked),
                ["false", "true"]
            );
            assert.deepEqual(getFacetTexts(target), [
                "Birthday: January 1997",
                "Birthday: Previous Year",
            ]);
            await removeFacet(target);
            assert.deepEqual(getFacetTexts(target), []);
        });

        QUnit.module("Favorite");
        QUnit.test(
            "simple rendering with no favorite (without ability to save)",
            async function (assert) {
                assert.expect(4);

                favoriteMenuRegistry.remove("custom-favorite-item");

                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchMenuTypes: ["favorite"],
                    searchViewId: false,
                    config: {
                        getDisplayName: () => "Action Name",
                    },
                });

                await toggleSearchBarMenu(target);
                assert.containsOnce(target, ".o_favorite_menu .fa.fa-star");
                assert.strictEqual(
                    target
                        .querySelector(".o_favorite_menu .o_dropdown_title")
                        .innerText.trim()
                        .toUpperCase(),
                    "FAVORITES"
                );
                assert.containsOnce(target, ".o_favorite_menu", "the menu should be opened");
                assert.containsNone(
                    target,
                    ".o_favorite_menu .o_menu_item",
                    "the menu should be empty"
                );
            }
        );

        QUnit.test("simple rendering with no favorite", async function (assert) {
            assert.expect(5);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["favorite"],
                searchViewId: false,
                config: {
                    getDisplayName: () => "Action Name",
                },
            });

            await toggleSearchBarMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .fa.fa-star");
            assert.strictEqual(
                target
                    .querySelector(".o_favorite_menu .o_dropdown_title")
                    .innerText.trim()
                    .toUpperCase(),
                "FAVORITES"
            );

            assert.containsOnce(target, ".o_favorite_menu", "the menu should be opened");
            assert.containsNone(target, ".o_favorite_menu .dropdown-divider");
            assert.containsOnce(target, ".o_favorite_menu .o_add_favorite");
        });

        QUnit.test("delete an active favorite", async function (assert) {
            assert.expect(14);

            class ToyController extends Component {
                setup() {
                    assert.deepEqual(this.props.domain, [["foo", "=", "qsdf"]]);
                    onWillUpdateProps((nextProps) => {
                        assert.deepEqual(nextProps.domain, []);
                    });
                }
            }
            ToyController.components = { SearchBar };
            ToyController.template = xml`
                <div>
                    <SearchBar/>
                </div>
            `;

            viewRegistry.add("toy", {
                type: "toy",
                display_name: "Toy",
                Controller: ToyController,
            });

            serverData.views["foo,false,toy"] = `<toy />`;
            serverData.models.foo.filters = [
                {
                    context: "{}",
                    domain: "[['foo', '=', 'qsdf']]",
                    id: 7,
                    is_default: true,
                    name: "My favorite",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ];

            const webClient = await createWebClient({
                serverData,
                mockRPC: async (_, args) => {
                    if (args.model === "ir.filters" && args.method === "unlink") {
                        assert.step("deleteFavorite");
                        return { result: true }; // mocked unlink result
                    }
                },
            });
            webClient.env.bus.addEventListener("CLEAR-CACHES", () => assert.step("CLEAR-CACHES"));
            await doAction(webClient, {
                name: "Action",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "toy"]],
            });

            await toggleSearchBarMenu(target);
            const favorite = target.querySelector(".o_favorite_menu .dropdown-item");
            assert.equal(favorite.innerText, "My favorite");
            assert.deepEqual(favorite.getAttribute("role"), "menuitemcheckbox");
            assert.deepEqual(favorite.ariaChecked, "true");

            assert.deepEqual(getFacetTexts(target), ["My favorite"]);
            assert.hasClass(target.querySelector(".o_favorite_menu .o_menu_item"), "selected");

            await deleteFavorite(target, 0);

            assert.verifySteps([]);

            await click(document.querySelector("div.o_dialog footer button"));

            assert.deepEqual(getFacetTexts(target), []);
            assert.containsOnce(target, ".o_favorite_menu .o_menu_item");
            assert.containsOnce(target, ".o_favorite_menu .o_add_favorite");
            assert.verifySteps(["deleteFavorite", "CLEAR-CACHES"]);
        });

        QUnit.test(
            "default favorite is not activated if activateFavorite is set to false",
            async function (assert) {
                assert.expect(3);

                const controlPanel = await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
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
                });

                await toggleSearchBarMenu(target);

                assert.notOk(isItemSelected(target, "My favorite"));
                assert.deepEqual(getDomain(controlPanel), []);
                assert.deepEqual(getFacetTexts(target), []);
            }
        );

        QUnit.test(
            'toggle favorite correctly clears filter, groupbys, comparison and field "options"',
            async function (assert) {
                patchDate(2019, 6, 31, 13, 43, 0);

                const searchBar = await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBar,
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
                });

                let domain = searchBar.env.searchModel.domain;
                let groupBy = searchBar.env.searchModel.groupBy;
                let comparison = searchBar.env.searchModel.getFullComparison();

                assert.deepEqual(domain, [
                    "&",
                    ["foo", "ilike", "a"],
                    "&",
                    ["date_field", ">=", "2019-01-01"],
                    ["date_field", "<=", "2019-12-31"],
                ]);
                assert.deepEqual(groupBy, ["date_field:month"]);
                assert.deepEqual(comparison, null);

                assert.deepEqual(getFacetTexts(target), [
                    "Foo\na",
                    "Date Field Filter: 2019",
                    "Date Field Groupby: Month",
                ]);

                // activate a comparison
                await toggleSearchBarMenu(target);
                await toggleMenuItem(target, "Date Field Filter: Previous Period");

                domain = searchBar.env.searchModel.domain;
                groupBy = searchBar.env.searchModel.groupBy;
                comparison = searchBar.env.searchModel.getFullComparison();

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
                const favorite = target.querySelector(".o_favorite_menu .dropdown-item");
                assert.equal(favorite.innerText, "My favorite");
                assert.deepEqual(favorite.getAttribute("role"), "menuitemcheckbox");
                assert.deepEqual(favorite.ariaChecked, "false");
                await toggleMenuItem(target.querySelector(".o_favorite_menu"), 0);
                assert.deepEqual(favorite.ariaChecked, "true");

                domain = searchBar.env.searchModel.domain;
                groupBy = searchBar.env.searchModel.groupBy;
                comparison = searchBar.env.searchModel.getFullComparison();

                assert.deepEqual(domain, ["!", ["foo", "=", "qsdf"]]);
                assert.deepEqual(groupBy, ["foo"]);
                assert.deepEqual(comparison, {
                    "favorite comparison content": "bla bla...",
                });

                assert.deepEqual(getFacetTexts(target), ["My favorite"]);
            }
        );

        QUnit.test("edit a favorite with a groupby", async function (assert) {
            const irFilters = [
                {
                    context: "{ 'some_key': 'some_value', 'group_by': ['bar'] }",
                    domain: "[('foo', 'ilike', 'abc')]",
                    id: 1,
                    is_default: true,
                    name: "My favorite",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ];
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
                searchViewId: false,
                searchViewArch: `<search/>`,
                irFilters,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), ["My favorite"]);

            await toggleSearchBarMenu(target);
            assert.containsNone(
                target,
                ".o_group_by_menu .o_menu_item:not(.o_add_custom_group_menu)"
            );

            await click(target, ".o_searchview_facet_label");
            assert.containsOnce(target, ".modal");

            await dsHelpers.editValue(target, "abcde");
            await click(target.querySelector(".modal footer button"));
            assert.containsNone(target, ".modal");
            assert.deepEqual(getFacetTexts(target), ["Bar", "Foo contains abcde"]);

            await toggleSearchBarMenu(target);
            assert.containsNone(
                target,
                ".o_group_by_menu .o_menu_item:not(.o_add_custom_group_menu)"
            );
        });

        QUnit.module("Group by");
        QUnit.test(
            "simple rendering with neither groupbys nor groupable fields",
            async function (assert) {
                assert.expect(3);

                serverData.views = {
                    "foo,false,search": `<search/>`,
                };

                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchMenuTypes: ["groupBy"],
                    searchViewId: false,
                    searchViewFields: {},
                });

                await toggleSearchBarMenu(target);

                assert.containsNone(target, ".o_menu_item");
                assert.containsNone(target, ".dropdown-divider");
                assert.containsNone(target, ".o_add_custom_group_menu");
            }
        );

        QUnit.test("simple rendering with no groupby", async function (assert) {
            assert.expect(3);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
            });

            await toggleSearchBarMenu(target);

            assert.containsOnce(target, ".o_menu_item");
            assert.containsNone(target, ".dropdown-divider");
            assert.containsOnce(target, ".o_add_custom_group_menu");
        });

        QUnit.test("simple rendering with a single groupby", async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);

            assert.containsN(target, ".o_menu_item", 2);
            const menuItem = target.querySelector(".o_menu_item");
            assert.strictEqual(menuItem.innerText.trim(), "Foo");
            assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
            assert.strictEqual(menuItem.ariaChecked, "false");
            assert.containsOnce(target, ".dropdown-divider");
            assert.containsOnce(target, ".o_add_custom_group_menu");
        });

        QUnit.test('toggle a "simple" groupby in groupby menu works', async function (assert) {
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
            assert.deepEqual(getFacetTexts(target), []);
            assert.notOk(isItemSelected(target, "Foo"));
            const menuItem = target.querySelector(".o_menu_item");
            assert.strictEqual(menuItem.innerText.trim(), "Foo");
            assert.strictEqual(menuItem.getAttribute("role"), "menuitemcheckbox");
            assert.strictEqual(menuItem.ariaChecked, "false");
            await toggleMenuItem(target, "Foo");
            assert.strictEqual(menuItem.ariaChecked, "true");

            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
            assert.deepEqual(getFacetTexts(target), ["Foo"]);
            assert.containsOnce(
                target.querySelector(".o_searchview .o_searchview_facet"),
                ".o_searchview_facet_label"
            );
            assert.ok(isItemSelected(target, "Foo"));

            await toggleMenuItem(target, "Foo");

            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
            assert.deepEqual(getFacetTexts(target), []);
            assert.notOk(isItemSelected(target, "Foo"));
        });

        QUnit.test('toggle a "simple" groupby quickly does not crash', async function (assert) {
            assert.expect(1);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);

            toggleMenuItem(target, "Foo");
            toggleMenuItem(target, "Foo");

            assert.ok(true);
        });

        QUnit.test(
            'remove a "Group By" facet properly unchecks groupbys in groupby menu',
            async function (assert) {
                assert.expect(6);

                const controlPanel = await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBar,
                    searchMenuTypes: ["groupBy"],
                    searchViewId: false,
                    searchViewArch: `
                    <search>
                        <filter string="Foo" name="group_by_foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                    context: { search_default_group_by_foo: 1 },
                });

                await toggleSearchBarMenu(target);

                assert.deepEqual(getFacetTexts(target), ["Foo"]);
                assert.deepEqual(controlPanel.env.searchModel.groupBy, ["foo"]);
                assert.ok(isItemSelected(target, "Foo"));

                await removeFacet(target, "Foo");

                assert.deepEqual(getFacetTexts(target), []);
                assert.deepEqual(controlPanel.env.searchModel.groupBy, []);

                await toggleSearchBarMenu(target);

                assert.notOk(isItemSelected(target, "Foo"));
            }
        );

        QUnit.test("group by a date field using interval works", async function (assert) {
            assert.expect(21);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                    </search>
                `,
                context: { search_default_date: 1 },
            });

            await toggleSearchBarMenu(target);

            assert.deepEqual(controlPanel.env.searchModel.groupBy, ["date_field:week"]);

            await toggleMenuItem(target, "Date");

            assert.ok(isOptionSelected(target, "Date", "Week"));

            assert.deepEqual(
                [...target.querySelectorAll(".o_item_option")].map((el) => el.innerText),
                ["Year", "Quarter", "Month", "Week", "Day"]
            );

            const steps = [
                {
                    description: "Year",
                    facetTexts: ["Date: Year\n>\nDate: Week"],
                    selectedoptions: ["Year", "Week"],
                    groupBy: ["date_field:year", "date_field:week"],
                },
                {
                    description: "Month",
                    facetTexts: ["Date: Year\n>\nDate: Month\n>\nDate: Week"],
                    selectedoptions: ["Year", "Month", "Week"],
                    groupBy: ["date_field:year", "date_field:month", "date_field:week"],
                },
                {
                    description: "Week",
                    facetTexts: ["Date: Year\n>\nDate: Month"],
                    selectedoptions: ["Year", "Month"],
                    groupBy: ["date_field:year", "date_field:month"],
                },
                {
                    description: "Month",
                    facetTexts: ["Date: Year"],
                    selectedoptions: ["Year"],
                    groupBy: ["date_field:year"],
                },
                {
                    description: "Year",
                    facetTexts: [],
                    selectedoptions: [],
                    groupBy: [],
                },
            ];
            for (const s of steps) {
                await toggleMenuItemOption(target, "Date", s.description);

                assert.deepEqual(controlPanel.env.searchModel.groupBy, s.groupBy);
                assert.deepEqual(getFacetTexts(target), s.facetTexts);
                s.selectedoptions.forEach((description) => {
                    assert.ok(isOptionSelected(target, "Date", description));
                });
            }
        });

        QUnit.test("interval options are correctly grouped and ordered", async function (assert) {
            assert.expect(8);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Bar" name="bar" context="{'group_by': 'bar'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'date_field'}"/>
                        <filter string="Foo" name="foo" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                context: { search_default_bar: 1 },
            });

            assert.deepEqual(getFacetTexts(target), ["Bar"]);

            // open menu 'Group By'
            await toggleSearchBarMenu(target);

            // Open the groupby 'Date'
            await toggleMenuItem(target, "Date");
            // select option 'week'
            await toggleMenuItemOption(target, "Date", "Week");

            assert.deepEqual(getFacetTexts(target), ["Bar\n>\nDate: Week"]);

            // select option 'day'
            await toggleMenuItemOption(target, "Date", "Day");

            assert.deepEqual(getFacetTexts(target), ["Bar\n>\nDate: Week\n>\nDate: Day"]);

            // select option 'year'
            await toggleMenuItemOption(target, "Date", "Year");

            assert.deepEqual(getFacetTexts(target), [
                "Bar\n>\nDate: Year\n>\nDate: Week\n>\nDate: Day",
            ]);

            // select 'Foo'
            await toggleMenuItem(target, "Foo");

            assert.deepEqual(getFacetTexts(target), [
                "Bar\n>\nDate: Year\n>\nDate: Week\n>\nDate: Day\n>\nFoo",
            ]);

            // select option 'quarter'
            await toggleMenuItemOption(target, "Date", "Quarter");

            assert.deepEqual(getFacetTexts(target), [
                "Bar\n>\nDate: Year\n>\nDate: Quarter\n>\nDate: Week\n>\nDate: Day\n>\nFoo",
            ]);

            // unselect 'Bar'
            await toggleMenuItem(target, "Bar");

            assert.deepEqual(getFacetTexts(target), [
                "Date: Year\n>\nDate: Quarter\n>\nDate: Week\n>\nDate: Day\n>\nFoo",
            ]);

            // unselect option 'week'
            await toggleMenuItemOption(target, "Date", "Week");

            assert.deepEqual(getFacetTexts(target), [
                "Date: Year\n>\nDate: Quarter\n>\nDate: Day\n>\nFoo",
            ]);
        });

        QUnit.test("default groupbys can be ordered", async function (assert) {
            assert.expect(2);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'date_field:week'}"/>
                    </search>
                `,
                context: { search_default_birthday: 2, search_default_date: 1 },
            });

            // the default groupbys should be activated in the right order
            assert.deepEqual(controlPanel.env.searchModel.groupBy, [
                "date_field:week",
                "birthday:month",
            ]);
            assert.deepEqual(getFacetTexts(target), ["Date: Week\n>\nBirthday: Month"]);
        });

        QUnit.test("a separator in groupbys does not cause problems", async function (assert) {
            assert.expect(23);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Date" name="coolName" context="{'group_by': 'date_field'}"/>
                        <separator/>
                        <filter string="Bar" name="superName" context="{'group_by': 'bar'}"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Date");
            await toggleMenuItemOption(target, "Date", "Day");

            assert.ok(isItemSelected(target, "Date"));
            assert.notOk(isItemSelected(target, "Bar"));
            assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
            assert.deepEqual(getFacetTexts(target), ["Date: Day"]);

            await toggleMenuItem(target, "Bar");

            assert.ok(isItemSelected(target, "Date"));
            assert.ok(isItemSelected(target, "Bar"));
            assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
            assert.deepEqual(getFacetTexts(target), ["Date: Day\n>\nBar"]);

            await toggleMenuItemOption(target, "Date", "Quarter");

            assert.ok(isItemSelected(target, "Date"));
            assert.ok(isItemSelected(target, "Bar"));
            assert.ok(isOptionSelected(target, "Date", "Quarter"), "selected");
            assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
            assert.deepEqual(getFacetTexts(target), ["Date: Quarter\n>\nDate: Day\n>\nBar"]);

            await toggleMenuItem(target, "Bar");

            assert.ok(isItemSelected(target, "Date"));
            assert.notOk(isItemSelected(target, "Bar"));
            assert.ok(isOptionSelected(target, "Date", "Quarter"), "selected");
            assert.ok(isOptionSelected(target, "Date", "Day"), "selected");
            assert.deepEqual(getFacetTexts(target), ["Date: Quarter\n>\nDate: Day"]);

            await removeFacet(target);

            assert.deepEqual(getFacetTexts(target), []);

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Date");

            assert.notOk(isItemSelected(target, "Date"));
            assert.notOk(isItemSelected(target, "Bar"));
            assert.notOk(isOptionSelected(target, "Date", "Quarter"), "selected");
            assert.notOk(isOptionSelected(target, "Date", "Day"), "selected");
        });

        QUnit.test("falsy search default groupbys are not activated", async function (assert) {
            assert.expect(2);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["groupBy"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                context: { search_default_birthday: false, search_default_foo: 0 },
            });

            assert.deepEqual(controlPanel.env.searchModel.groupBy, []);
            assert.deepEqual(getFacetTexts(target), []);
        });

        QUnit.test(
            "Custom group by menu is displayed when hideCustomGroupBy is not set",
            async function (assert) {
                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchViewId: false,
                    searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                    searchMenuTypes: ["groupBy"],
                });

                await toggleSearchBarMenu(target);

                assert.containsOnce(target, ".o_add_custom_group_menu");
            }
        );

        QUnit.test(
            "Custom group by menu is displayed when hideCustomGroupBy is false",
            async function (assert) {
                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchViewId: false,
                    searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                    hideCustomGroupBy: false,
                    searchMenuTypes: ["groupBy"],
                });

                await toggleSearchBarMenu(target);

                assert.containsOnce(target, ".o_add_custom_group_menu");
            }
        );

        QUnit.test(
            "Custom group by menu is displayed when hideCustomGroupBy is true",
            async function (assert) {
                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchViewId: false,
                    searchViewArch: `
                    <search>
                        <filter string="Birthday" name="birthday" context="{'group_by': 'birthday'}"/>
                        <filter string="Date" name="date" context="{'group_by': 'foo'}"/>
                    </search>
                `,
                    hideCustomGroupBy: true,
                    searchMenuTypes: ["groupBy"],
                });

                await toggleSearchBarMenu(target);

                assert.containsNone(target, ".o_add_custom_group_menu");
            }
        );

        QUnit.module("Filter");

        QUnit.test("simple rendering with no filter", async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["filter"],
            });

            await toggleSearchBarMenu(target);
            assert.containsOnce(target, ".o_menu_item");
            assert.containsNone(target, ".dropdown-divider");
            assert.containsOnce(target, ".dropdown-item");
            assert.strictEqual(
                target.querySelector(".dropdown-item").innerText,
                "Add Custom Filter"
            );
        });

        QUnit.test("simple rendering with a single filter", async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="foo" domain="[]"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);
            assert.containsN(target, ".o_menu_item", 2);
            assert.containsOnce(target, ".o_menu_item[role=menuitemcheckbox]");
            assert.deepEqual(target.querySelector(".o_menu_item").ariaChecked, "false");
            assert.containsOnce(target, ".dropdown-divider");
            assert.containsN(target, ".o_menu_item", 2);
            assert.strictEqual(
                target.querySelector(".o_menu_item:nth-of-type(2)").innerText,
                "Add Custom Filter"
            );
        });

        QUnit.test('toggle a "simple" filter in filter menu works', async function (assert) {
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="foo" domain="[('foo', '=', 'qsdf')]"/>
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);
            assert.deepEqual(getFacetTexts(target), []);
            assert.notOk(isItemSelected(target, "Foo"));
            assert.deepEqual(getDomain(controlPanel), []);
            assert.containsOnce(target, ".o_menu_item[role=menuitemcheckbox]");
            assert.deepEqual(target.querySelector(".o_menu_item").ariaChecked, "false");

            await toggleMenuItem(target, "Foo");
            assert.deepEqual(target.querySelector(".o_menu_item").ariaChecked, "true");

            assert.deepEqual(getFacetTexts(target), ["Foo"]);
            assert.containsOnce(
                target.querySelector(".o_searchview .o_searchview_facet"),
                ".o_searchview_facet_label"
            );
            assert.ok(isItemSelected(target, "Foo"));
            assert.deepEqual(getDomain(controlPanel), [["foo", "=", "qsdf"]]);

            await toggleMenuItem(target, "Foo");

            assert.deepEqual(getFacetTexts(target), []);
            assert.notOk(isItemSelected(target, "Foo"));
            assert.deepEqual(getDomain(controlPanel), []);
        });

        QUnit.test("filter by a date field using period works", async function (assert) {
            assert.expect(57);

            patchDate(2017, 2, 22, 1, 0, 0);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Date" name="date_field" date="date_field"/>
                    </search>
                `,
                context: { search_default_date_field: 1 },
            });

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Date");

            const optionEls = target.querySelectorAll(".dropdown .o_item_option");

            // default filter should be activated with the global default period 'this_month'
            assert.deepEqual(getDomain(controlPanel), [
                "&",
                ["date_field", ">=", "2017-03-01"],
                ["date_field", "<=", "2017-03-31"],
            ]);
            assert.ok(isItemSelected(target, "Date"));
            assert.ok(isOptionSelected(target, "Date", "March"));

            // check option descriptions
            const optionDescriptions = [...optionEls].map((e) => e.innerText.trim());
            const expectedDescriptions = [
                "March",
                "February",
                "January",
                "Q4",
                "Q3",
                "Q2",
                "Q1",
                "2017",
                "2016",
                "2015",
            ];
            assert.deepEqual(optionDescriptions, expectedDescriptions);

            // check generated domains
            const steps = [
                {
                    toggledOption: "March",
                    resultingFacet: "Date: 2017",
                    selectedoptions: ["2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "February",
                    resultingFacet: "Date: February 2017",
                    selectedoptions: ["February", "2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-02-01"],
                        ["date_field", "<=", "2017-02-28"],
                    ],
                },
                {
                    toggledOption: "February",
                    resultingFacet: "Date: 2017",
                    selectedoptions: ["2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "January",
                    resultingFacet: "Date: January 2017",
                    selectedoptions: ["January", "2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-01-31"],
                    ],
                },
                {
                    toggledOption: "Q4",
                    resultingFacet: "Date: January 2017/Q4 2017",
                    selectedoptions: ["January", "Q4", "2017"],
                    domain: [
                        "|",
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-01-31"],
                        "&",
                        ["date_field", ">=", "2017-10-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "January",
                    resultingFacet: "Date: Q4 2017",
                    selectedoptions: ["Q4", "2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-10-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "Q4",
                    resultingFacet: "Date: 2017",
                    selectedoptions: ["2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "Q1",
                    resultingFacet: "Date: Q1 2017",
                    selectedoptions: ["Q1", "2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-03-31"],
                    ],
                },
                {
                    toggledOption: "Q1",
                    resultingFacet: "Date: 2017",
                    selectedoptions: ["2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "2017",
                    selectedoptions: [],
                    domain: [],
                },
                {
                    toggledOption: "2017",
                    resultingFacet: "Date: 2017",
                    selectedoptions: ["2017"],
                    domain: [
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "2016",
                    resultingFacet: "Date: 2016/2017",
                    selectedoptions: ["2017", "2016"],
                    domain: [
                        "|",
                        "&",
                        ["date_field", ">=", "2016-01-01"],
                        ["date_field", "<=", "2016-12-31"],
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "2015",
                    resultingFacet: "Date: 2015/2016/2017",
                    selectedoptions: ["2017", "2016", "2015"],
                    domain: [
                        "|",
                        "&",
                        ["date_field", ">=", "2015-01-01"],
                        ["date_field", "<=", "2015-12-31"],
                        "|",
                        "&",
                        ["date_field", ">=", "2016-01-01"],
                        ["date_field", "<=", "2016-12-31"],
                        "&",
                        ["date_field", ">=", "2017-01-01"],
                        ["date_field", "<=", "2017-12-31"],
                    ],
                },
                {
                    toggledOption: "March",
                    resultingFacet: "Date: March 2015/March 2016/March 2017",
                    selectedoptions: ["March", "2017", "2016", "2015"],
                    domain: [
                        "|",
                        "&",
                        ["date_field", ">=", "2015-03-01"],
                        ["date_field", "<=", "2015-03-31"],
                        "|",
                        "&",
                        ["date_field", ">=", "2016-03-01"],
                        ["date_field", "<=", "2016-03-31"],
                        "&",
                        ["date_field", ">=", "2017-03-01"],
                        ["date_field", "<=", "2017-03-31"],
                    ],
                },
            ];
            for (const s of steps) {
                await toggleMenuItemOption(target, "Date", s.toggledOption);
                assert.deepEqual(getDomain(controlPanel), s.domain);
                if (s.resultingFacet) {
                    assert.deepEqual(getFacetTexts(target), [s.resultingFacet]);
                } else {
                    assert.deepEqual(getFacetTexts(target), []);
                }
                s.selectedoptions.forEach((option) => {
                    assert.ok(
                        isOptionSelected(target, "Date", option),
                        `at step ${steps.indexOf(s) + 1}, ${option} should be selected`
                    );
                });
            }
        });

        QUnit.test(
            "filter by a date field using period works even in January",
            async function (assert) {
                assert.expect(5);

                patchDate(2017, 0, 7, 3, 0, 0);

                const controlPanel = await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBar,
                    searchViewId: false,
                    searchMenuTypes: ["filter"],
                    searchViewArch: `
                        <search>
                            <filter string="Date" name="some_filter" date="date_field" default_period="last_month"/>
                        </search>
                    `,
                    context: { search_default_some_filter: 1 },
                });

                assert.deepEqual(getDomain(controlPanel), [
                    "&",
                    ["date_field", ">=", "2016-12-01"],
                    ["date_field", "<=", "2016-12-31"],
                ]);

                assert.deepEqual(getFacetTexts(target), ["Date: December 2016"]);

                await toggleSearchBarMenu(target);
                await toggleMenuItem(target, "Date");

                assert.ok(isItemSelected(target, "Date"));
                assert.ok(isOptionSelected(target, "Date", "December"));
                assert.ok(isOptionSelected(target, "Date", "2016"));
            }
        );

        QUnit.test("`context` key in <filter> is used", async function (assert) {
            assert.expect(1);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Filter" name="some_filter" domain="[]" context="{'coucou_1': 1}"/>
                    </search>
                `,
                context: { search_default_some_filter: 1 },
            });

            assert.deepEqual(getContext(controlPanel), {
                coucou_1: 1,
                lang: "en",
                tz: "taht",
                uid: 7,
            });
        });

        QUnit.test("Filter with JSON-parsable domain works", async function (assert) {
            assert.expect(1);

            const xml_domain = "[[&quot;foo&quot;,&quot;=&quot;,&quot;Gently Weeps&quot;]]";

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Foo" name="gently_weeps" domain="${xml_domain}"/>
                    </search>
                `,
                context: { search_default_gently_weeps: 1 },
            });

            assert.deepEqual(
                getDomain(controlPanel),
                [["foo", "=", "Gently Weeps"]],
                "A JSON parsable xml domain should be handled just like any other"
            );
        });

        QUnit.test("filter with date attribute set as search_default", async function (assert) {
            assert.expect(1);

            patchDate(2019, 6, 31, 13, 43, 0);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Date" name="date_field" date="date_field" default_period="last_month"/>
                    </search>
                `,
                context: { search_default_date_field: true },
            });

            assert.deepEqual(getFacetTexts(target), ["Date: June 2019"]);
        });

        QUnit.test(
            "filter with multiple values in default_period date attribute set as search_default",
            async function (assert) {
                assert.expect(3);

                patchDate(2019, 6, 31, 13, 43, 0);

                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchViewId: false,
                    searchMenuTypes: ["filter"],
                    searchViewArch: `
                        <search>
                            <filter string="Date" name="date_field" date="date_field" default_period="this_year,last_year"/>
                        </search>
                    `,
                    context: { search_default_date_field: true },
                });

                await toggleSearchBarMenu(target);
                await toggleMenuItem(target, "Date");

                assert.ok(isItemSelected(target, "Date"));
                assert.ok(isOptionSelected(target, "Date", "2019"));
                assert.ok(isOptionSelected(target, "Date", "2018"));
            }
        );

        QUnit.test("filter domains are correcly combined by OR and AND", async function (assert) {
            assert.expect(2);

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
                        <filter string="Filter Group 1" name="f_1_g1" domain="[['foo', '=', 'f1_g1']]"/>
                        <separator/>
                        <filter string="Filter 1 Group 2" name="f1_g2" domain="[['foo', '=', 'f1_g2']]"/>
                        <filter string="Filter 2 GROUP 2" name="f2_g2" domain="[['foo', '=', 'f2_g2']]"/>
                    </search>
                `,
                context: {
                    search_default_f_1_g1: true,
                    search_default_f1_g2: true,
                    search_default_f2_g2: true,
                },
            });

            assert.deepEqual(getDomain(controlPanel), [
                "&",
                ["foo", "=", "f1_g1"],
                "|",
                ["foo", "=", "f1_g2"],
                ["foo", "=", "f2_g2"],
            ]);

            assert.deepEqual(getFacetTexts(target), [
                "Filter Group 1",
                "Filter 1 Group 2\nor\nFilter 2 GROUP 2",
            ]);
        });

        QUnit.test("arch order of groups of filters preserved", async function (assert) {
            assert.expect(12);

            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchViewId: false,
                searchMenuTypes: ["filter"],
                searchViewArch: `
                    <search>
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
                    </search>
                `,
            });

            await toggleSearchBarMenu(target);
            assert.containsN(target, ".o_filter_menu .o_menu_item", 12);

            const menuItemEls = target.querySelectorAll(
                ".o_filter_menu .o_menu_item:not(.o_add_custom_filter)"
            );
            menuItemEls.forEach((e, index) => {
                assert.strictEqual(e.innerText.trim(), String(index + 1));
            });
        });

        QUnit.test("Open 'Add Custom Filter' dialog", async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["filter"],
            });

            await toggleSearchBarMenu(target);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_filter_menu .dropdown-item")),
                ["Add Custom Filter"]
            );
            assert.containsNone(target, ".modal");

            await openAddCustomFilterDialog(target);
            assert.containsOnce(target, ".modal");
            assert.strictEqual(
                target.querySelector(".modal header").innerText,
                "Add Custom Filter"
            );
            assert.containsOnce(target, ".modal .o_domain_selector");
            assert.containsOnce(target, ".modal .o_domain_selector .o_tree_editor_condition");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".modal footer button")), [
                "Add",
                "Cancel",
            ]);
        });

        QUnit.test(
            "Default leaf in 'Add Custom Filter' dialog is based on ID (if no special fields on model)",
            async function (assert) {
                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchMenuTypes: ["filter"],
                });
                await toggleSearchBarMenu(target);
                await openAddCustomFilterDialog(target);
                assert.containsOnce(target, ".modal .o_domain_selector .o_tree_editor_condition");
                assert.containsOnce(
                    target,
                    ".o_tree_editor_condition .o_model_field_selector_chain_part"
                );
                assert.strictEqual(dsHelpers.getCurrentPath(target), "ID");
            }
        );

        QUnit.test(
            "Default leaf in 'Add Custom Filter' dialog is based on first special field (if any special fields on model)",
            async function (assert) {
                serverData.models.foo.fields.country_id = {
                    string: "Country",
                    type: "many2one",
                    relation: "country",
                };
                await makeWithSearch({
                    serverData,
                    resModel: "foo",
                    Component: SearchBarMenu,
                    searchMenuTypes: ["filter"],
                });
                await toggleSearchBarMenu(target);
                await openAddCustomFilterDialog(target);
                assert.containsOnce(target, ".modal .o_domain_selector .o_tree_editor_condition");
                assert.containsOnce(
                    target,
                    ".o_tree_editor_condition .o_model_field_selector_chain_part"
                );
                assert.strictEqual(dsHelpers.getCurrentPath(target), "Country");
            }
        );

        QUnit.test("Default connector is '|' (any)", async function (assert) {
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBarMenu,
                searchMenuTypes: ["filter"],
            });
            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            assert.containsOnce(target, ".modal .o_domain_selector .o_tree_editor_condition");
            assert.containsOnce(
                target,
                ".o_tree_editor_condition .o_model_field_selector_chain_part"
            );
            assert.strictEqual(dsHelpers.getCurrentPath(target), "ID");
            assert.containsOnce(target, ".o_domain_selector .o_tree_editor_connector");

            await dsHelpers.clickOnButtonAddNewRule(target);
            assert.containsOnce(target, ".o_domain_selector .dropdown-toggle");
            assert.strictEqual(
                target.querySelector(".o_domain_selector .dropdown-toggle").innerText,
                "any"
            );
            assert.containsN(target, ".modal .o_domain_selector .o_tree_editor_condition", 2);
        });

        QUnit.test("Add a custom filter", async function (assert) {
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Filter" name="filter" domain="[('foo', '=', 'abc')]"/>
                    </search>
                `,
                context: {
                    search_default_filter: true,
                },
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), ["Filter"]);
            assert.deepEqual(getDomain(controlPanel), [["foo", "=", "abc"]]);

            await toggleSearchBarMenu(target);
            assert.containsOnce(target, ".o_filter_menu .o_menu_item:not(.o_add_custom_filter)");

            await openAddCustomFilterDialog(target);
            await dsHelpers.clickOnButtonAddNewRule(target);

            await click(target.querySelector(".o_domain_selector .dropdown .dropdown-toggle"));
            await click(target.querySelector(".o_domain_selector .dropdown .dropdown-item"));

            await dsHelpers.clickOnButtonAddBranch(target, -1);
            await dsHelpers.clickOnButtonAddBranch(target, -1);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [
                "Filter",
                "ID = 1",
                "ID = 1",
                "( ID = 1 and ID = 1 ) or ID is in ( 1 , 1 )",
            ]);
            assert.deepEqual(getDomain(controlPanel), [
                "&",
                ["foo", "=", "abc"],
                "&",
                ["id", "=", 1],
                "&",
                ["id", "=", 1],
                "|",
                "|",
                ["id", "=", 1],
                ["id", "=", 1],
                "&",
                ["id", "=", 1],
                ["id", "=", 1],
            ]);

            // open again the search menu -> the custom filter should not be displayed
            await toggleSearchBarMenu(target);
            assert.containsOnce(target, ".o_filter_menu .o_menu_item:not(.o_add_custom_filter)");
        });

        QUnit.test("Add a custom filter containing an expression", async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(getDomain(controlPanel), []);

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(
                target,
                dsHelpers.SELECTORS.debugArea,
                `[("foo", "in", [uid, 1, "a"])]`
            );
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [`Foo is in ( uid , 1 , "a" )`]);
            assert.deepEqual(getDomain(controlPanel), [
                ["foo", "in", [7, 1, "a"]], // uid = 7
            ]);
        });

        QUnit.test("Add a custom filter containing a between operator", async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(getDomain(controlPanel), []);

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(target, dsHelpers.SELECTORS.debugArea, `[("id", "between", [0, 10])]`);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [`ID is between 0 and 10`]);
            assert.deepEqual(getDomain(controlPanel), ["&", ["id", ">=", 0], ["id", "<=", 10]]);
        });

        QUnit.test("consistent display of ! in debug mode", async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(
                target,
                dsHelpers.SELECTORS.debugArea,
                `["!", "|", ("foo", "=", 1 ), ("id", "=", 2)]`
            );
            assert.strictEqual(
                target.querySelector(".o_tree_editor_row .dropdown-toggle").textContent,
                "none"
            );

            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [`! ( Foo = 1 or ID = 2 )`]);
            assert.deepEqual(getDomain(controlPanel), ["!", "|", ["foo", "=", 1], ["id", "=", 2]]);
        });

        QUnit.test("display of is (not) (not) set in facets", async function (assert) {
            serverData.models.foo.fields.boolean = {
                type: "boolean",
                string: "Boolean",
                searchable: true,
            };
            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(getDomain(controlPanel), []);

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await dsHelpers.selectOperator(target, "not_set");
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["ID is not set"]);
            assert.deepEqual(getDomain(controlPanel), [["id", "=", false]]);

            await click(target, ".o_searchview_facet_label");
            await dsHelpers.selectOperator(target, "set");
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["ID is set"]);
            assert.deepEqual(getDomain(controlPanel), [["id", "!=", false]]);

            await click(target, ".o_searchview_facet_label");
            await openModelFieldSelectorPopover(target);
            await click(target.querySelector(".o_model_field_selector_popover_item_name"));
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["Boolean is set"]);
            assert.deepEqual(getDomain(controlPanel), [["boolean", "=", true]]);

            await click(target, ".o_searchview_facet_label");
            await dsHelpers.selectValue(target, false);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["Boolean is not set"]);
            assert.deepEqual(getDomain(controlPanel), [["boolean", "=", false]]);

            await click(target, ".o_searchview_facet_label");
            await dsHelpers.selectOperator(target, "is_not");
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["Boolean is not not set"]);
            assert.deepEqual(getDomain(controlPanel), [["boolean", "!=", false]]);

            await click(target, ".o_searchview_facet_label");
            await dsHelpers.selectValue(target, true);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["Boolean is not set"]);
            assert.deepEqual(getDomain(controlPanel), [["boolean", "!=", true]]);
        });

        QUnit.test("Add a custom filter: notification on invalid domain", async function (assert) {
            assert.expect(3);
            patchWithCleanup(odoo, { debug: true });
            registry.category("services").add(
                "notification",
                {
                    start() {
                        return {
                            add(message, options) {
                                assert.strictEqual(message, "Domain is invalid. Please correct it");
                                assert.deepEqual(options, { type: "danger" });
                            },
                        };
                    },
                },
                { force: true }
            );
            await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return false;
                    }
                },
            });

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(target, dsHelpers.SELECTORS.debugArea, "[(uid, uid, uid)]");
            await click(target.querySelector(".modal footer button"));
            assert.containsOnce(target, ".modal .o_domain_selector");
        });

        QUnit.test("display names in facets", async function (assert) {
            patchWithCleanup(odoo, { debug: true });
            serverData.models.partner = {
                fields: {},
                records: [
                    { id: 1, display_name: "John" },
                    { id: 2, display_name: "David" },
                ],
            };

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(
                target,
                dsHelpers.SELECTORS.debugArea,
                `[("bar", "=", 1 ), ("bar", "in", [2, 5555]), ("bar", "!=", false), ("id", "=", 2)]`
            );
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [
                "Bar = John",
                "Bar is in ( David , Inaccessible/missing record ID: 5555 )",
                "Bar != false",
                "ID = 2",
            ]);
            assert.deepEqual(getDomain(controlPanel), [
                "&",
                ["bar", "=", 1],
                "&",
                ["bar", "in", [2, 5555]],
                "&",
                ["bar", "!=", false],
                ["id", "=", 2],
            ]);
        });

        QUnit.test("display names in facets (with a property)", async function (assert) {
            patchWithCleanup(odoo, { debug: true });
            serverData.models.partner = {
                fields: {},
                records: [{ id: 1, display_name: "John" }],
            };

            async function mockRPC(route, { method, model }) {
                if (route === "/web/domain/validate") {
                    return true;
                }
                if (method === "web_search_read" && model === "parentModel") {
                    return {
                        records: [
                            {
                                id: 1337,
                                display_name: "First Parent",
                                properties_definition: [
                                    {
                                        name: "m2o",
                                        type: "many2one",
                                        string: "M2O",
                                        comodel: "partner",
                                    },
                                ],
                            },
                        ],
                    };
                }
            }

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC,
            });
            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            await editInput(target, dsHelpers.SELECTORS.debugArea, `[("properties.m2o", "=", 1)]`);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), ["Properties 🠒 M2O = John"]);
            assert.deepEqual(getDomain(controlPanel), [["properties.m2o", "=", 1]]);
        });

        QUnit.test("group by properties", async function (assert) {
            assert.expect(11);

            async function mockRPC(route, { method, model, args, kwargs }) {
                if (method === "web_search_read" && model === "parentModel") {
                    assert.step("definitionFetched");
                    const records = [
                        {
                            id: 1337,
                            display_name: "First Parent",
                            properties_definition: [
                                {
                                    name: "my_text",
                                    type: "text",
                                    string: "My Text",
                                },
                                {
                                    name: "my_partner",
                                    type: "many2one",
                                    string: "My Partner",
                                    comodel: "res.partner",
                                },
                                {
                                    name: "my_datetime",
                                    type: "datetime",
                                    string: "My Datetime",
                                },
                            ],
                        },
                        {
                            id: 1338,
                            display_name: "Second Parent",
                            properties_definition: [
                                {
                                    name: "my_integer",
                                    type: "integer",
                                    string: "My Integer",
                                },
                            ],
                        },
                    ];
                    return { records };
                }
            }

            patchWithCleanup(browser, { setTimeout: (fn) => fn() });

            const searchBar = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchViewId: false,
                searchViewArch: `
                    <search>
                        <filter string="Properties" name="properties" context="{'group_by': 'properties'}"/>
                    </search>
                `,
                hideCustomGroupBy: true,
                searchMenuTypes: ["groupBy"],
                mockRPC,
            });

            // definition is fetched only when we open the properties menu
            assert.verifySteps([]);

            await click(target, ".o_searchview_dropdown_toggler");

            // definition is fetched only when we open the properties menu
            assert.verifySteps([]);
            const items = [...target.querySelectorAll(".o_menu_item")];
            assert.deepEqual(
                items.map((item) => item.innerText),
                ["Properties"]
            );

            await click(target, ".o_accordion_toggle");
            await nextTick();

            // now that we open the properties we fetch the definition
            assert.verifySteps(["definitionFetched"]);

            const propertiesItems = [
                ...target.querySelectorAll(".o_accordion_values .dropdown-item"),
            ];
            assert.deepEqual(
                propertiesItems.map((item) => item.innerText),
                [
                    "My Text (First Parent)",
                    "My Partner (First Parent)",
                    "My Datetime (First Parent)",
                    "My Integer (Second Parent)",
                ]
            );

            // open the datetime item
            await click(propertiesItems[2]);

            const optionsItems = [
                ...target.querySelectorAll(
                    ".o_accordion_values .o_accordion_values .dropdown-item"
                ),
            ];
            assert.deepEqual(
                optionsItems.map((item) => item.innerText),
                ["Year", "Quarter", "Month", "Week", "Day"]
            );

            assert.deepEqual(searchBar.env.searchModel.groupBy, []);
            assert.deepEqual(getFacetTexts(target), []);

            await optionsItems[1].click();
            await nextTick();

            assert.deepEqual(searchBar.env.searchModel.groupBy, ["properties.my_datetime:quarter"]);
            assert.deepEqual(getFacetTexts(target), ["My Datetime: Quarter"]);
        });

        QUnit.test("shorten descriptions of long lists", async function (assert) {
            patchWithCleanup(odoo, { debug: true });

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getFacetTexts(target), []);
            assert.deepEqual(getDomain(controlPanel), []);

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);
            const values = new Array(500).fill(42525245);

            await editInput(target, dsHelpers.SELECTORS.debugArea, `[("id", "in", [${values}])]`);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [
                `ID is in ( ${values.slice(0, 20).join(" , ")} , ... )`,
            ]);
            assert.deepEqual(getDomain(controlPanel), [["id", "in", values]]);
        });

        QUnit.test(`Custom filter with "&"" as value`, async function (assert) {
            serverData.models.foo.fields.active = {
                type: "boolean",
                string: "Active",
                searchable: true,
            };
            patchWithCleanup(odoo, { debug: true });

            const controlPanel = await makeWithSearch({
                serverData,
                resModel: "foo",
                Component: SearchBar,
                searchMenuTypes: ["filter"],
                searchViewId: false,
                searchViewArch: `<search />`,
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            assert.deepEqual(getDomain(controlPanel), []);

            await toggleSearchBarMenu(target);
            await openAddCustomFilterDialog(target);

            await editInput(target, dsHelpers.SELECTORS.debugArea, `[("foo", "ilike", "&")]`);
            await click(target.querySelector(".modal footer button"));

            assert.deepEqual(getFacetTexts(target), [`Foo contains &`]);
            assert.deepEqual(getDomain(controlPanel), [["foo", "ilike", "&"]]);
        });
    });
});
