import { after, expect, test } from "@odoo/hoot";
import { press, queryAllTexts } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    editFavoriteName,
    editSearch,
    fields,
    getFacetTexts,
    mockService,
    models,
    mountWithSearch,
    onRpc,
    saveFavorite,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";

import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { useSetupAction } from "@web/search/action_hook";

class Foo extends models.Model {
    bar = fields.Many2one({ relation: "partner" });
    birthday = fields.Date();
    date_field = fields.Date();
    float_field = fields.Float();
    foo = fields.Char();
}

class Partner extends models.Model {}

defineModels([Foo, Partner]);

test("simple rendering", async () => {
    await mountWithSearch(
        SearchBar,
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
    await toggleSaveFavorite();
    expect(`.o_add_favorite + .o_accordion_values input[type="text"]`).toHaveValue("Action Name");
    expect(`.o_add_favorite + .o_accordion_values input[type="checkbox"]`).toHaveCount(2);
    expect(queryAllTexts(`.o_add_favorite + .o_accordion_values .form-check label`)).toEqual([
        "Default filter",
        "Shared",
    ]);
});

test("favorites use by default and share are exclusive", async () => {
    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["favorite"],
        searchViewId: false,
    });

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    expect(`input[type="checkbox"]`).toHaveCount(2);
    expect(`input[type="checkbox"]:checked`).toHaveCount(0);

    await contains(`input[type="checkbox"]:eq(0)`).check();
    expect(`input[type="checkbox"]:eq(0)`).toBeChecked();
    expect(`input[type="checkbox"]:eq(1)`).not.toBeChecked();

    await contains(`input[type="checkbox"]:eq(1)`).check();
    expect(`input[type="checkbox"]:eq(0)`).not.toBeChecked();
    expect(`input[type="checkbox"]:eq(1)`).toBeChecked();

    await contains(`input[type="checkbox"]:eq(0)`).check();
    expect(`input[type="checkbox"]:eq(0)`).toBeChecked();
    expect(`input[type="checkbox"]:eq(1)`).not.toBeChecked();

    await contains(`input[type="checkbox"]:eq(0)`).uncheck();
    expect(`input[type="checkbox"]:eq(0)`).not.toBeChecked();
    expect(`input[type="checkbox"]:eq(1)`).not.toBeChecked();
});

test("save filter", async () => {
    class TestComponent extends Component {
        static components = { SearchBarMenu };
        static template = xml`<div><SearchBarMenu/></div>`;
        static props = ["*"];
        setup() {
            useSetupAction({
                getContext: () => {
                    return { someKey: "foo" };
                },
            });
        }
    }
    onRpc("create_or_replace", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.context).toEqual({ group_by: [], someKey: "foo" });
        return 7; // fake serverSideId
    });

    const component = await mountWithSearch(TestComponent, {
        resModel: "foo",
        context: { someOtherKey: "bar" }, // should not end up in filter's context
        searchViewId: false,
    });
    const clearCacheListener = () => expect.step("CLEAR-CACHES");
    component.env.bus.addEventListener("CLEAR-CACHES", clearCacheListener);
    after(() => component.env.bus.removeEventListener("CLEAR-CACHES", clearCacheListener));
    expect.verifySteps([]);

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("aaa");
    await saveFavorite();
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_or_replace", "CLEAR-CACHES"]);
});

test("dynamic filters are saved dynamic", async () => {
    onRpc("create_or_replace", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.domain).toBe(
            `[("date_field", ">=", (context_today() + relativedelta()).strftime("%Y-%m-%d"))]`
        );
        return 7; // fake serverSideId
    });

    await mountWithSearch(SearchBar, {
        resModel: "foo",
        context: { search_default_filter: 1 },
        searchMenuTypes: ["filter", "favorite"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Filter" name="filter" domain="[('date_field', '>=', (context_today() + relativedelta()).strftime('%Y-%m-%d'))]"/>
            </search>
        `,
    });
    expect(getFacetTexts()).toEqual(["Filter"]);

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("My favorite");
    await saveFavorite();
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_or_replace"]);
});

test("save filters created via autocompletion works", async () => {
    onRpc("create_or_replace", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.domain).toBe(`[("foo", "ilike", "a")]`);
        return 7; // fake serverSideId
    });

    await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchMenuTypes: ["favorite"],
        searchViewId: false,
        searchViewArch: `<search><field name="foo"/></search>`,
    });
    expect(getFacetTexts()).toEqual([]);

    await editSearch("a");
    await validateSearch();
    expect(getFacetTexts()).toEqual(["Foo\na"]);

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("My favorite");
    await saveFavorite();
    expect(getFacetTexts()).toEqual(["My favorite"]);
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_or_replace"]);
});

test("favorites have unique descriptions (the submenus of the favorite menu are correctly updated)", async () => {
    mockService("notification", {
        add(message, options) {
            expect.step("notification");
            expect(message).toBe("A filter with same name already exists.");
            expect(options).toEqual({ type: "danger" });
        },
    });

    onRpc("create_or_replace", ({ args, route }) => {
        expect.step(route);
        expect(args[0]).toEqual({
            action_id: false,
            context: { group_by: [] },
            domain: `[]`,
            is_default: false,
            model_id: "foo",
            name: "My favorite 2",
            sort: `[]`,
            embedded_action_id: false,
            embedded_parent_res_id: false,
            user_id: 7,
        });
        return 2; // fake serverSideId
    });

    await mountWithSearch(SearchBar, {
        resModel: "foo",
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
    });

    await toggleSearchBarMenu();
    await toggleSaveFavorite();

    // first try: should fail
    await editFavoriteName("My favorite");
    await saveFavorite();
    expect.verifySteps(["notification"]);

    // second try: should succeed
    await editFavoriteName("My favorite 2");
    await saveFavorite();
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_or_replace"]);

    // third try: should fail
    await editFavoriteName("My favorite 2");
    await saveFavorite();
    expect.verifySteps(["notification"]);
});

test("undefined name for filter shows notification and not error", async () => {
    mockService("notification", {
        add(message, options) {
            expect.step("notification");
            expect(message).toBe("A name for your favorite filter is required.");
            expect(options).toEqual({ type: "danger" });
        },
    });

    onRpc("create_or_replace", () => 7); // fake serverSideId

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
    });

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await saveFavorite();
    expect.verifySteps(["notification"]);
});

test("add favorite with enter which already exists", async () => {
    mockService("notification", {
        add(message, options) {
            expect.step("notification");
            expect(message).toBe("A name for your favorite filter is required.");
            expect(options).toEqual({ type: "danger" });
        },
    });
    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
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
    });

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("My favorite");
    await press("Enter");

    expect.verifySteps(["notification"]);
});
