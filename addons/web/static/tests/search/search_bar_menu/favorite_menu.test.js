import { after, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { editValue } from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    editFavorite,
    getFacetTexts,
    isItemSelected,
    mockService,
    mountWithSearch,
    onRpc,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { defineSearchBarModels } from "./models";

import { registry } from "@web/core/registry";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

const favoriteMenuRegistry = registry.category("favoriteMenu");

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

test("edit an active favorite", async () => {
    const irFilters = [
        {
            context: "{}",
            domain: "[['foo', '=', 'qsdf']]",
            id: 7,
            is_default: true,
            name: "My favorite",
            sort: "[]",
            user_ids: [2],
        },
    ];
    mockService("action", {
        doAction(action) {
            expect.step("edit favorite");
            expect(action).toEqual({
                context: {
                    form_view_ref: "base.ir_filters_view_edit_form",
                },
                type: "ir.actions.act_window",
                res_model: "ir.filters",
                views: [[false, "form"]],
                res_id: 7,
            });
        },
    });
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["favorite"],
        searchViewId: false,
        searchViewArch: `<search/>`,
        irFilters,
    });
    expect(getFacetTexts()).toEqual(["My favorite"]);

    await toggleSearchBarMenu();
    const favorite = queryFirst`.o_favorite_menu .dropdown-item`;
    expect(favorite).toHaveText("My favorite");
    expect(favorite).toHaveAttribute("role", "menuitemcheckbox");
    expect(favorite).toHaveProperty("ariaChecked", "true");
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect(queryFirst`.o_favorite_menu .o_menu_item`).toHaveClass("selected");

    await editFavorite("My favorite");
    expect.verifySteps(["edit favorite"]);
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
                user_ids: [2],
            },
        ],
        activateFavorite: false,
    });
    await toggleSearchBarMenu();
    expect(isItemSelected("My favorite")).toBe(false);
    expect(searchBarMenu.env.searchModel.domain).toEqual([]);
    expect(getFacetTexts()).toEqual([]);
});

test(`toggle favorite correctly clears filter, groupbys and field "options"`, async () => {
    mockDate("2019-07-31T13:43:00");

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["filter", "groupBy", "favorite"],
        searchViewId: false,
        irFilters: [
            {
                context: `{"group_by": ["foo"]}`,
                domain: "['!', ['foo', '=', 'qsdf']]",
                id: 7,
                is_default: false,
                name: "My favorite",
                sort: "[]",
                user_ids: [2],
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
    expect(getFacetTexts()).toEqual([
        "Foo\na",
        "Date Field Filter: 2019",
        "Date Field Groupby: Month",
    ]);

    // activate the unique existing favorite
    await toggleSearchBarMenu();
    const favorite = queryFirst`.o_favorite_menu .dropdown-item`;
    expect(favorite).toHaveText("My favorite");
    expect(favorite).toHaveAttribute("role", "menuitemcheckbox");
    expect(favorite).toHaveProperty("ariaChecked", "false");

    await toggleMenuItem("My favorite");
    expect(favorite).toHaveProperty("ariaChecked", "true");
    expect(searchBar.env.searchModel.domain).toEqual(["!", ["foo", "=", "qsdf"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["foo"]);
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
            user_ids: [2],
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
    expect(getFacetTexts()).toEqual(["Foo contains abcde", "Bar"]);

    await toggleSearchBarMenu();
    expect(`.o_group_by_menu .o_menu_item:not(.o_add_custom_group_menu)`).toHaveCount(0);
});

test("shared favorites are partially shown if there is more than 4", async () => {
    const irFilters = [];
    for (let i = 1; i < 6; i++) {
        irFilters.push({
            context: "{}",
            domain: "[('foo', '=', 'a')]",
            id: i,
            is_default: false,
            name: "My favorite" + i,
            sort: "[]",
            user_ids: [],
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
    expect(".o_favorite_menu .o_favorite_item").toHaveCount(3);
    expect(".o_favorite_menu .o_expand_shared_favorites").toHaveCount(1);
    await contains(".o_favorite_menu .o_expand_shared_favorites").click();
    expect(".o_favorite_menu .o_expand_shared_favorites").toHaveCount(0);
    expect(".o_favorite_menu .o_favorite_item").toHaveCount(5);
});
