import { after, expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import {
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
    saveAndEditFavorite,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";

import { useSetupAction } from "@web/search/action_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { rpcBus } from "@web/core/network/rpc";

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
    expect(`.o_add_favorite + .o_accordion_values input[type="checkbox"]`).toHaveCount(1);
    expect(`.o_add_favorite + .o_accordion_values .form-check label`).toHaveText("Default filter");
});

test("save filter", async () => {
    class TestComponent extends Component {
        static components = { SearchBarMenu };
        static template = xml`<div><SearchBarMenu/></div>`;
        static props = ["*"];
        setup() {
            useSetupAction({
                getContext: () => ({ someKey: "foo" }),
            });
        }
    }
    onRpc("create_filter", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.context).toEqual({ group_by: [], someKey: "foo" });
        return [7]; // fake serverSideId
    });

    await mountWithSearch(TestComponent, {
        resModel: "foo",
        context: { someOtherKey: "bar" }, // should not end up in filter's context
        searchViewId: false,
    });
    const clearCacheListener = () => expect.step("CLEAR-CACHES");
    rpcBus.addEventListener("CLEAR-CACHES", clearCacheListener);
    after(() => rpcBus.removeEventListener("CLEAR-CACHES", clearCacheListener));
    expect.verifySteps([]);

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("aaa");
    await saveFavorite();
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_filter", "CLEAR-CACHES"]);
});

test("save and edit filter", async () => {
    class TestComponent extends Component {
        static components = { SearchBarMenu };
        static template = xml`<div><SearchBarMenu/></div>`;
        static props = ["*"];
        setup() {
            useSetupAction({
                getContext: () => ({ someKey: "foo" }),
            });
        }
    }
    onRpc("create_filter", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.context).toEqual({ group_by: [], someKey: "foo" });
        return [7]; // fake serverSideId
    });
    mockService("action", {
        doAction(action) {
            expect(action).toEqual({
                context: {
                    form_view_ref: "base.ir_filters_view_edit_form",
                },
                res_id: 7,
                res_model: "ir.filters",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            });
            expect.step("Edit favorite");
        },
    });

    await mountWithSearch(TestComponent, {
        resModel: "foo",
        context: { someOtherKey: "bar" }, // should not end up in filter's context
        searchViewId: false,
    });
    const clearCacheListener = () => expect.step("CLEAR-CACHES");
    rpcBus.addEventListener("CLEAR-CACHES", clearCacheListener);
    after(() => rpcBus.removeEventListener("CLEAR-CACHES", clearCacheListener));
    expect.verifySteps([]);

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await editFavoriteName("aaa");
    await saveAndEditFavorite();
    expect.verifySteps([
        "/web/dataset/call_kw/ir.filters/create_filter",
        "CLEAR-CACHES",
        "Edit favorite",
    ]);
});

test("dynamic filters are saved dynamic", async () => {
    onRpc("create_filter", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.domain).toBe(
            `[("date_field", ">=", (context_today() + relativedelta()).strftime("%Y-%m-%d"))]`
        );
        return [7]; // fake serverSideId
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
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_filter"]);
});

test("save filters created via autocompletion works", async () => {
    onRpc("create_filter", ({ args, route }) => {
        expect.step(route);
        const irFilter = args[0];
        expect(irFilter.domain).toBe(`[("foo", "ilike", "a")]`);
        return [7]; // fake serverSideId
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
    expect.verifySteps(["/web/dataset/call_kw/ir.filters/create_filter"]);
});

test("undefined name for filter shows notification and not error", async () => {
    mockService("notification", {
        add(message, options) {
            expect.step("notification");
            expect(message).toBe("A name for your favorite filter is required.");
            expect(options).toEqual({ type: "danger" });
        },
    });

    onRpc("create_filter", () => [7]); // fake serverSideId

    await mountWithSearch(SearchBarMenu, {
        resModel: "foo",
        searchViewId: false,
    });

    await toggleSearchBarMenu();
    await toggleSaveFavorite();
    await saveFavorite();
    expect.verifySteps(["notification"]);
});
