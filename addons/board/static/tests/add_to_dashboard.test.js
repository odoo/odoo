import { addToBoardItem } from "@board/add_to_board/add_to_board";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { hover, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import * as dsHelpers from "@web/../tests/core/domain_selector/domain_selector_helpers";
import {
    contains,
    defineModels,
    fields,
    getDropdownMenu,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    openAddCustomFilterDialog,
    removeFacet,
    selectGroup,
    serverState,
    switchView,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

class Board extends models.Model {}

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char({
        string: "Foo",
        default: "My little Foo Value",
        searchable: true,
    });
    bar = fields.Boolean({ string: "Bar" });
    int_field = fields.Integer({
        string: "Integer field",
        aggregator: "sum",
    });

    _records = [
        {
            id: 1,
            name: "first record",
            foo: "yop",
            int_field: 3,
        },
        {
            id: 2,
            name: "second record",
            foo: "lalala",
            int_field: 5,
        },
        {
            id: 4,
            name: "aaa",
            foo: "abc",
            int_field: 2,
        },
    ];
}

defineModels([Board, Partner]);
defineMailModels();
const favoriteMenuRegistry = registry.category("favoriteMenu");

function getAddToDashboardMenu() {
    return getDropdownMenu(".o_add_to_board button.dropdown-toggle");
}

beforeEach(() => {
    favoriteMenuRegistry.add("add-to-board", addToBoardItem, { sequence: 10 });
});

test("save actions to dashboard", async () => {
    expect.assertions(6);

    Partner._views = {
        list: '<list><field name="foo"/></list>',
        search: "<search></search>",
    };

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        expect(args.context_to_save.group_by).toEqual(["foo"], {
            message: "The group_by should have been saved",
        });
        expect(args.context_to_save.orderedBy).toEqual(
            [
                {
                    name: "foo",
                    asc: true,
                },
            ],
            { message: "The orderedBy should have been saved" }
        );
        expect(args.context_to_save.fire).toBe("on the bayou", {
            message: "The context of a controller should be passed and flattened",
        });
        expect(args.action_id).toBe(1, { message: "should save the correct action" });
        expect(args.view_mode).toBe("list", { message: "should save the correct view type" });
        return true;
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        context: { fire: "on the bayou" },
        views: [[false, "list"]],
    });

    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });

    // Sort the list
    await contains(".o_column_sortable").click();

    // Group It
    await toggleSearchBarMenu();
    await selectGroup("foo");

    // add this action to dashboard
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("input", { root: getAddToDashboardMenu() })).edit("a name", {
        confirm: false,
    });
    await contains(queryOne("button", { root: getAddToDashboardMenu() })).click();
});

test("save two searches to dashboard", async () => {
    // the second search saved should not be influenced by the first
    expect.assertions(2);

    Partner._views = {
        list: '<list><field name="foo"/></list>',
        search: `
            <search>
                <filter name="filter_on_a" string="Filter on a" domain="[['name', 'ilike', 'a']]"/>
                <filter name="filter_on_b" string="Filter on b" domain="[['name', 'ilike', 'b']]"/>
            </search>
        `,
    };

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        if (filter_count === 0) {
            expect(args.domain).toEqual([["name", "ilike", "a"]], {
                message: "the correct domain should be sent",
            });
        }
        if (filter_count === 1) {
            expect(args.domain).toEqual([["name", "ilike", "b"]], {
                message: "the correct domain should be sent",
            });
        }

        filter_count += 1;
        return true;
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });

    var filter_count = 0;
    // Add a first filter
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter on a");

    // Add it to dashboard
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("button", { root: getAddToDashboardMenu() })).click();

    // Remove it
    await removeFacet("Filter on a");

    // Add the second filter
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter on b");

    // Add it to dashboard
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("button", { root: getAddToDashboardMenu() })).click();
});

test("save an action domain to dashboard", async () => {
    // View domains are to be added to the dashboard domain
    expect.assertions(1);

    var view_domain = ["name", "ilike", "a"];
    var filter_domain = ["name", "ilike", "b"];

    var expected_domain = ["&", view_domain, filter_domain];

    Partner._views = {
        list: '<list><field name="foo"/></list>',
        search: `
            <search>
                <filter name="filter" string="Filter" domain="[['name', 'ilike', 'b']]"/>
            </search>
        `,
    };

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        expect(args.domain).toEqual(expected_domain, {
            message: "the correct domain should be sent",
        });
        return true;
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
        domain: [view_domain],
    });

    // Add a filter
    await toggleSearchBarMenu();
    await toggleMenuItem("Filter");

    // Add it to dashboard
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    // add
    await contains(queryOne("button", { root: getAddToDashboardMenu() })).click();
});

test("add to dashboard with no action id", async () => {
    expect.assertions(2);

    Partner._views = {
        pivot: '<pivot><field name="foo"/></pivot>',
        search: "<search/>",
    };
    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: false,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await toggleSearchBarMenu();
    expect(".o_add_to_board").toHaveCount(0);

    // Sanity check
    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await toggleSearchBarMenu();
    expect(".o_add_to_board").toHaveCount(1);
});

test("correctly save the time ranges of a reporting view in comparison mode", async () => {
    expect.assertions(1);

    mockDate("2020-07-01 11:00:00");

    Partner._fields.date = fields.Date();

    Partner._views = {
        pivot: '<pivot><field name="foo"/></pivot>',
        search: '<search><filter name="Date" date="date"/></search>',
    };

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        expect(args.context_to_save.comparison).toEqual({
            domains: [
                {
                    arrayRepr: ["&", ["date", ">=", "2020-07-01"], ["date", "<=", "2020-07-31"]],
                    description: "July 2020",
                },
                {
                    arrayRepr: ["&", ["date", ">=", "2020-06-01"], ["date", "<=", "2020-06-30"]],
                    description: "June 2020",
                },
            ],
            fieldName: "date",
        });
        return true;
    });

    // makes mouseEnter work

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    // filter on July 2020
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "July");

    // compare July 2020 to June 2020
    await toggleMenuItem("Date: Previous Period");

    // add the view to the dashboard

    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("input", { root: getAddToDashboardMenu() })).edit("Pipeline", {
        confirm: false,
    });
    await contains(queryOne("button", { root: getAddToDashboardMenu() })).click();
});

test("Add a view to dashboard (keynav)", async () => {
    Partner._views = {
        pivot: '<pivot><field name="foo"/></pivot>',
        search: "<search/>",
    };

    // makes mouseEnter work

    onRpc("/board/add_to_dashboard", () => {
        expect.step("add to board");
        return true;
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });

    await toggleSearchBarMenu();
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("input", { root: getAddToDashboardMenu() })).edit("Pipeline", {
        confirm: false,
    });
    await press("Enter");

    expect.verifySteps(["add to board"]);
});

test("Add a view with dynamic domain", async () => {
    expect.assertions(1);

    Partner._views = {
        pivot: '<pivot><field name="foo"/></pivot>',
        search: `
            <search>
                <filter name="filter" domain="[('user_id','=',uid)]"/>
            </search>`,
    };

    // makes mouseEnter work

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        expect(args.domain).toEqual(["&", ["int_field", "<=", 3], ["user_id", "=", 7]]);
        return true;
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
        domain: [["int_field", "<=", 3]],
        context: { search_default_filter: 1 },
    });

    await toggleSearchBarMenu();
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("input", { root: getAddToDashboardMenu() })).edit("Pipeline");
});

test("Add a view to dashboard doesn't save default filters", async () => {
    expect.assertions(2);

    Partner._views = {
        pivot: '<pivot><field name="foo"/></pivot>',
        list: '<list><field name="foo"/></list>',
        search: `
            <search>
                <filter name="filter" domain="[('foo','!=','yop')]"/>
            </search>`,
    };

    // makes mouseEnter work
    serverState.debug = true;

    onRpc("/board/add_to_dashboard", async (request) => {
        const { params: args } = await request.json();
        expect(args.domain).toEqual([["foo", "=", "yop"]]);
        expect(args.context_to_save).toEqual({
            pivot_measures: ["__count"],
            pivot_column_groupby: [],
            pivot_row_groupby: [],
            orderedBy: [],
            group_by: [],
            dashboard_merge_domains_contexts: false,
        });
        return true;
    });
    onRpc("/web/domain/validate", () => {
        return true;
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "pivot"],
        ],
        context: { search_default_filter: 1 },
    });

    await switchView("pivot");

    // Remove default filter ['foo', '!=', 'yop']
    await removeFacet("filter");

    // Add a filter ['foo', '=', 'yop']
    await toggleSearchBarMenu();
    await openAddCustomFilterDialog();
    await contains(dsHelpers.SELECTORS.debugArea).edit(`[("foo", "=", "yop")]`);
    await contains(".modal footer button").click();

    // Add to dashboard
    await toggleSearchBarMenu();
    await hover(".o_add_to_board button.dropdown-toggle");
    await animationFrame();
    await contains(queryOne("input", { root: getAddToDashboardMenu() })).edit("Pipeline");
});

test("Add to my dashboard is not available in form views", async () => {
    Partner._views = {
        list: '<list><field name="foo"/></list>',
        form: '<form><field name="foo"/></form>',
        search: "<search></search>",
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        context: { fire: "on the bayou" },
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });

    expect(".o_list_view").toHaveCount(1, { message: "should display the list view" });

    // sanity check
    await contains(".o_cp_action_menus .dropdown-toggle").click();
    expect(".o-dropdown--menu .o_add_to_board").toHaveCount(1);

    // open form view
    await contains(".o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_cp_action_menus .dropdown-toggle").click();
    expect(".o-dropdown--menu").toHaveCount(1);
    expect(".o-dropdown--menu .o_add_to_board").toHaveCount(0);
});
