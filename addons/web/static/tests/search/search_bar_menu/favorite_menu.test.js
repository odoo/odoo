import { after, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Component, onWillUpdateProps, xml } from "@odoo/owl";
import { editValue } from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    deleteFavorite,
    editFavoriteName,
    getFacetTexts,
    getService,
    isItemSelected,
    mountWithCleanup,
    mountWithSearch,
    onRpc,
    patchWithCleanup,
    saveFavorite,
    serverState,
    toggleMenuItem,
    toggleSaveFavorite,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { Foo, defineSearchBarModels } from "./models";

import { registry } from "@web/core/registry";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { WebClient } from "@web/webclient/webclient";

const favoriteMenuRegistry = registry.category("favoriteMenu");
const viewsRegistry = registry.category("views");

defineSearchBarModels();

test("simple rendering with no favorite (without ability to save)", async () => {
    const registryItem = favoriteMenuRegistry.content["custom-favorite-item"];
    favoriteMenuRegistry.remove("custom-favorite-item");
    after(() => {
        favoriteMenuRegistry.add("custom-favorite-item", registryItem[1], {
            sequence: registryItem[1],
        });
    });

    await mountWithSearch(
        SearchBarMenu,
        {
            resModel: "foo",
            searchMenuTypes: ["favorite"],
            searchViewId: false,
        },
        { getDisplayName: () => "Action Name" }
    );

    await toggleSearchBarMenu();
    expect(`.o_favorite_menu .fa.fa-star`).toHaveCount(1);
    expect(`.o_favorite_menu .o_dropdown_title`).toHaveText(/^favorites$/i);
    expect(`.o_favorite_menu`).toHaveCount(1);
    expect(`.o_favorite_menu .o_menu_item`).toHaveCount(0);
});

test("simple rendering with no favorite", async () => {
    await mountWithSearch(
        SearchBarMenu,
        {
            resModel: "foo",
            searchMenuTypes: ["favorite"],
            searchViewId: false,
        },
        {
            getDisplayName: () => "Action Name",
        }
    );

    await toggleSearchBarMenu();
    expect(`.o_favorite_menu .fa.fa-star`).toHaveCount(1);
    expect(`.o_favorite_menu .o_dropdown_title`).toHaveText(/^favorites$/i);
    expect(`.o_favorite_menu`).toHaveCount(1);
    expect(`.o_favorite_menu .dropdown-divider`).toHaveCount(0);
    expect(`.o_favorite_menu .o_add_favorite`).toHaveCount(1);
});

test("delete an active favorite", async () => {
    class ToyController extends Component {
        static components = { SearchBar };
        static template = xml`<div><SearchBar/></div>`;
        static props = ["*"];

        setup() {
            expect(this.props.domain).toEqual([["foo", "=", "qsdf"]]);
            onWillUpdateProps((nextProps) => {
                expect.step("props updated");
                expect(nextProps.domain).toEqual([]);
            });
        }
    }

    patchWithCleanup(serverState.view_info, {
        toy: { multi_record: true, display_name: "Toy", icon: "fab fa-android" },
    });
    viewsRegistry.add("toy", {
        type: "toy",
        Controller: ToyController,
    });
    after(() => viewsRegistry.remove("toy"));
    Foo._views.toy = `<toy/>`;
    Foo._filters = [
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

    onRpc("unlink", () => {
        expect.step("deleteFavorite");
        return true;
    });

    const webClient = await mountWithCleanup(WebClient);

    const clearCacheListener = () => expect.step("CLEAR-CACHES");
    webClient.env.bus.addEventListener("CLEAR-CACHES", clearCacheListener);
    after(() => webClient.env.bus.removeEventListener("CLEAR-CACHES", clearCacheListener));

    await getService("action").doAction({
        name: "Action",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "toy"]],
    });
    await toggleSearchBarMenu();
    const favorite = queryFirst`.o_favorite_menu .dropdown-item`;
    expect(favorite).toHaveText("My favorite");
    expect(favorite).toHaveAttribute("role", "menuitemcheckbox");
    expect(favorite).toHaveProperty("ariaChecked", "true");
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect(queryFirst`.o_favorite_menu .o_menu_item`).toHaveClass("selected");

    await deleteFavorite("My favorite");
    expect.verifySteps([]);

    await contains(`div.o_dialog footer button`).click();
    expect(getFacetTexts()).toEqual([]);
    expect(".o_favorite_menu .o_menu_item").toHaveCount(1);
    expect(".o_favorite_menu .o_add_favorite").toHaveCount(1);
    expect.verifySteps(["deleteFavorite", "CLEAR-CACHES", "props updated"]);
});

test("default favorite is not activated if activateFavorite is set to false", async () => {
    const searchBarMenu = await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
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
    await toggleSearchBarMenu();
    expect(isItemSelected("My favorite")).toBe(false);
    expect(searchBarMenu.env.searchModel.domain).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
});

test(`toggle favorite correctly clears filter, groupbys, comparison and field "options"`, async () => {
    mockDate("2019-07-31T13:43:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
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
                <filter string="Date Field Filter" name="positive" date="date_field" default_period="year"/>
                <filter string="Date Field Groupby" name="coolName" context="{'group_by': 'date_field'}"/>
            </search>
        `,
        context: {
            search_default_positive: true,
            search_default_coolName: true,
            search_default_foo: "a",
        },
    });
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["foo", "ilike", "a"],
        "&",
        ["date_field", ">=", "2019-01-01"],
        ["date_field", "<=", "2019-12-31"],
    ]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:month"]);
    expect(searchBar.env.searchModel.getFullComparison()).toBe(null);
    expect(getFacetTexts()).toEqual([
        "Foo\na",
        "Date Field Filter: 2019",
        "Date Field Groupby: Month",
    ]);

    // activate a comparison
    await toggleSearchBarMenu();
    await toggleMenuItem("Date Field Filter: Previous Period");
    expect(searchBar.env.searchModel.domain).toEqual([["foo", "ilike", "a"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_field:month"]);
    expect(searchBar.env.searchModel.getFullComparison()).toEqual({
        comparisonId: "previous_period",
        comparisonRange: [
            "&",
            ["date_field", ">=", "2018-01-01"],
            ["date_field", "<=", "2018-12-31"],
        ],
        comparisonRangeDescription: "2018",
        fieldDescription: "Date Field Filter",
        fieldName: "date_field",
        range: ["&", ["date_field", ">=", "2019-01-01"], ["date_field", "<=", "2019-12-31"]],
        rangeDescription: "2019",
    });

    // activate the unique existing favorite
    const favorite = queryFirst`.o_favorite_menu .dropdown-item`;
    expect(favorite).toHaveText("My favorite");
    expect(favorite).toHaveAttribute("role", "menuitemcheckbox");
    expect(favorite).toHaveProperty("ariaChecked", "false");

    await toggleMenuItem("My favorite");
    expect(favorite).toHaveProperty("ariaChecked", "true");
    expect(searchBar.env.searchModel.domain).toEqual(["!", ["foo", "=", "qsdf"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["foo"]);
    expect(searchBar.env.searchModel.getFullComparison()).toEqual({
        "favorite comparison content": "bla bla...",
    });
    expect(getFacetTexts()).toEqual(["My favorite"]);
});

test("edit a favorite with a groupby", async () => {
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

    onRpc("/web/domain/validate", () => true);
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["groupBy"], // we need it to have facet (see facets getter in search_model)
        searchViewId: false,
        searchViewArch: `<search/>`,
        irFilters,
    });
    expect(getFacetTexts()).toEqual(["My favorite"]);

    await toggleSearchBarMenu();
    expect(`.o_group_by_menu .o_menu_item:not(.o_add_custom_group_menu)`).toHaveCount(0);

    await contains(`.o_searchview_facet_label`).click();
    expect(`.modal`).toHaveCount(1);

    await editValue("abcde");
    await contains(`.modal footer button`).click();
    expect(`.modal`).toHaveCount(0);
    expect(getFacetTexts()).toEqual(["Bar", "Foo contains abcde"]);

    await toggleSearchBarMenu();
    expect(`.o_group_by_menu .o_menu_item:not(.o_add_custom_group_menu)`).toHaveCount(0);
});

test("shared favorites are grouped under a dropdown if there are more than 10", async () => {
    onRpc("create_or_replace", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.domain).toBe(`[]`);
        return 10; // fake serverSideId
    });
    const irFilters = [];
    for (let i = 1; i < 11; i++) {
        irFilters.push({
            context: "{}",
            domain: "[('foo', '=', 'a')]",
            id: i,
            is_default: false,
            name: "My favorite" + i,
            sort: "[]",
        });
    }
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchMenuTypes: ["favorite"],
        searchViewId: false,
        irFilters,
        activateFavorite: false,
    });
    await toggleSearchBarMenu();
    expect(".o_favorite_menu .o-dropdown-item").toHaveCount(10);
    await toggleSaveFavorite();
    await editFavoriteName("My favorite11");
    await contains(".o-checkbox:eq(1)").click();
    await saveFavorite();
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_or_replace"]);
    expect(".o_favorite_menu .o-dropdown-item").toHaveCount(0);
    expect(".o_favorite_menu .o_menu_item:contains(Shared filters)").toHaveCount(1);
    await contains(".o_favorite_menu .o_menu_item:contains(Shared filters)").click();
    expect(".o_favorite_menu .o-dropdown-item").toHaveCount(11);
});
