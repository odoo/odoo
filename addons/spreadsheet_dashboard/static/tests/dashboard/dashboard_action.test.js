import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, press, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getBasicData, Product } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import {
    contains,
    editFavoriteName,
    mockService,
    onRpc,
    patchWithCleanup,
    saveAndEditFavorite,
    saveFavorite,
    toggleSaveFavorite,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { RPCError } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";
import { range } from "@web/core/utils/numbers";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/helpers/global_filter";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

function getServerData(spreadsheetData) {
    const serverData = getDashboardServerData();
    serverData.models = {
        ...serverData.models,
        ...getBasicData(),
    };
    serverData.models["spreadsheet.dashboard.group"].records = [
        {
            published_dashboard_ids: [789],
            id: 1,
            name: "Pivot",
        },
    ];
    serverData.models["spreadsheet.dashboard"].records = [
        {
            id: 789,
            name: "Spreadsheet with Pivot",
            json_data: JSON.stringify(spreadsheetData),
            spreadsheet_data: JSON.stringify(spreadsheetData),
            dashboard_group_id: 1,
        },
    ];
    return serverData;
}

test("display available spreadsheets", async () => {
    await createSpreadsheetDashboard();
    expect(".o_search_panel section").toHaveCount(2);
    expect(".o_search_panel li").toHaveCount(3);
});

test("display the active spreadsheet", async () => {
    await createSpreadsheetDashboard();
    expect(".o_search_panel li.active").toHaveCount(1, {
        message: "It should have one active element",
    });
    expect(".o-spreadsheet").toHaveCount(1, { message: "It should display the spreadsheet" });
});

test("Fold/unfold the search panel", async function () {
    await createSpreadsheetDashboard();
    await contains(".o_spreadsheet_dashboard_search_panel button").click();
    expect(".o_spreadsheet_dashboard_search_panel").toHaveCount(0);
    expect(".o_search_panel_sidebar").toHaveText("Container 1 / Dashboard CRM 1");
    await contains(".o_search_panel_sidebar button").click();
    expect(".o_search_panel_sidebar").toHaveCount(0);
    expect(".o_spreadsheet_dashboard_search_panel").toHaveCount(1);
});

test("Folding dashboard from 'FAVORITES' group shows correct active dashboard group", async function () {
    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (
                args.method === "action_toggle_favorite" &&
                args.model === "spreadsheet.dashboard"
            ) {
                expect.step("action_toggle_favorite");
                return true;
            }
        },
    });

    await contains(".o_dashboard_star").click();
    expect(".o_search_panel_section").toHaveCount(3);
    expect(".o_search_panel_category header b:first").toHaveText("FAVORITES");
    expect.verifySteps(["action_toggle_favorite"]);

    await contains(".o_spreadsheet_dashboard_search_panel button").click();
    expect(".o_spreadsheet_dashboard_search_panel").toHaveCount(0);
    expect(".o_search_panel_sidebar").toHaveText("Container 1 / Dashboard CRM 1");
});

test("Fold button invisible in the search panel without any dashboard", async function () {
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard"].records = [];
    serverData.models["spreadsheet.dashboard.group"].records = [];
    await createSpreadsheetDashboard({ serverData });
    expect(".o_spreadsheet_dashboard_search_panel button").toHaveCount(0);
});

test("load action with specific dashboard", async () => {
    await createSpreadsheetDashboard({ spreadsheetId: 3 });
    expect(".o_search_panel li.active").toHaveText("Dashboard Accounting 1");
});

test("can switch spreadsheet", async () => {
    await createSpreadsheetDashboard();
    const spreadsheets = queryAll(".o_search_panel li");

    expect(spreadsheets[0]).toHaveClass("active");
    expect(spreadsheets[1]).not.toHaveClass("active");
    expect(spreadsheets[2]).not.toHaveClass("active");

    await contains(spreadsheets[1]).click();

    expect(spreadsheets[0]).not.toHaveClass("active");
    expect(spreadsheets[1]).toHaveClass("active");
    expect(spreadsheets[2]).not.toHaveClass("active");
});

test("display no dashboard message", async () => {
    await createSpreadsheetDashboard({
        mockRPC: function (route, { model, method, args }) {
            if (method === "web_search_read" && model === "spreadsheet.dashboard.group") {
                return {
                    records: [],
                    length: 0,
                };
            }
        },
    });
    expect(".o_search_panel li").toHaveCount(0, {
        message: "It should not display any spreadsheet",
    });
    expect(".dashboard-loading-status").toHaveText("No available dashboard", {
        message: "It should display no dashboard message",
    });
});

test("display error message", async () => {
    expect.errors(1);
    onRpc("/spreadsheet/dashboard/data/2", () => {
        const error = new RPCError();
        error.data = {};
        throw error;
    });
    await createSpreadsheetDashboard();
    expect(".o-spreadsheet").toHaveCount(1, { message: "It should display the spreadsheet" });
    await contains(".o_search_panel li:eq(1)").click();
    expect(".o_spreadsheet_dashboard_action .dashboard-loading-status.error").toHaveCount(1, {
        message: "It should display an error",
    });
    await contains(".o_search_panel li:eq(0)").click();
    expect(".o-spreadsheet").toHaveCount(1, { message: "It should display the spreadsheet" });
    expect(".o_renderer .error").toHaveCount(0, { message: "It should not display an error" });
    expect.verifyErrors(["RPC_ERROR"]);
});

test("load dashboard that doesn't exist", async () => {
    expect.errors(1);
    await createSpreadsheetDashboard({
        spreadsheetId: 999,
    });
    expect(".o_spreadsheet_dashboard_action .dashboard-loading-status.error").toHaveCount(1, {
        message: "It should display an error",
    });
    expect.verifyErrors(["RPC_ERROR"]);
});

test("Last selected spreadsheet is kept when go back from breadcrumb", async function () {
    const spreadsheetData = {
        version: 16,
        sheets: [
            {
                id: "sheet1",
                cells: { A1: { content: '=PIVOT.VALUE("1", "probability")' } },
            },
        ],
        pivots: {
            1: {
                id: 1,
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
            },
        },
    };
    const serverData = getServerData(spreadsheetData);
    serverData.models["spreadsheet.dashboard"].records.push({
        id: 790,
        name: "Second dashboard",
        json_data: JSON.stringify(spreadsheetData),
        spreadsheet_data: JSON.stringify(spreadsheetData),
        dashboard_group_id: 1,
    });
    serverData.models["spreadsheet.dashboard.group"].records[0].published_dashboard_ids.push(790);
    await createSpreadsheetDashboard({ serverData });
    await contains(".o_search_panel li:last-child").click();
    await contains(".o-dashboard-clickable-cell").click();
    expect(".o_list_view").toHaveCount(1);
    await contains(".o_back_button").click();
    expect(".o_search_panel li:last-child").toHaveClass("active");
});

test("Can clear filter date filter value that defaults to current period", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "Period",
            },
            {
                id: "2",
                type: "date",
                label: "This Year",
                defaultValue: "this_year",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });
    const year = luxon.DateTime.local().year;
    expect(".o_control_panel_actions .o_facet_value").toHaveText(String(year));
    await contains(".o_searchview_facet_label").click();
    await contains('.o-filter-item[data-id="2"] input').click();
    await contains(".o-dropdown-item[data-id='year'] .btn-previous").click();
    await contains(".o-filter-values-footer .btn-primary").click();

    expect(".o_control_panel_actions .o_facet_value").toHaveText(String(year - 1));

    expect(".o_control_panel_actions .o_facet_remove").toHaveCount(1);
    await contains(".o_control_panel_actions .o_facet_remove").click();

    expect(".o_control_panel_actions .o_facet_remove").toHaveCount(0);
});

test("share dashboard from dashboard view", async function () {
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: (url) => {
            expect.step("share url copied");
            expect(url).toBe("localhost:8069/share/url/132465");
        },
    });
    const def = new Deferred();
    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (args.method === "action_get_share_url") {
                await def;
                expect.step("dashboard_shared");
                expect(args.model).toBe("spreadsheet.dashboard.share");
                return "localhost:8069/share/url/132465";
            }
        },
    });
    expect(".spreadsheet_share_dropdown").toHaveCount(0);
    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(".spreadsheet_share_dropdown .o_loading_state").toHaveText("Generating sharing link");
    def.resolve();
    await animationFrame();
    expect(".spreadsheet_share_dropdown .o_loading_state").toHaveCount(0);
    expect.verifySteps(["dashboard_shared", "share url copied"]);
    expect(".o_field_CopyClipboardChar").toHaveText("localhost:8069/share/url/132465");
    await contains(".fa-clipboard").click();
    expect.verifySteps(["share url copied"]);
});

test("Changing filter values will create a new share", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "Period",
            },
            {
                id: "2",
                type: "date",
                label: "This Year",
                defaultValue: "this_year",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    let counter = 0;
    await createSpreadsheetDashboard({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "action_get_share_url") {
                return `localhost:8069/share/url/${++counter}`;
            }
        },
    });
    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(".o_field_CopyClipboardChar").toHaveText(`localhost:8069/share/url/1`);

    await contains("i.fa-share-alt").click(); // close share dropdown

    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(".o_field_CopyClipboardChar").toHaveText(`localhost:8069/share/url/1`);

    await contains("i.fa-share-alt").click();
    const year = luxon.DateTime.local().year;
    expect(".o_control_panel_actions .o_facet_value").toHaveText(String(year));
    await contains(".o_searchview_facet_label").click();
    await contains(".o-filter-value input").click();
    await contains(".o-dropdown-item[data-id='year'] .btn-previous").click();
    await contains(".o-filter-values-footer .btn-primary").click();

    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(".o_field_CopyClipboardChar").toHaveText(`localhost:8069/share/url/2`);
});

test("Should toggle favorite status of a dashboard when the 'Favorite' icon is clicked", async function () {
    onRpc("spreadsheet.dashboard", "action_toggle_favorite", ({ method }) => {
        expect.step(method);
        return true;
    });
    await createSpreadsheetDashboard();
    expect(".o_search_panel_section").toHaveCount(2);
    await contains(".o_dashboard_star").click();
    expect(".o_dashboard_star").toHaveClass("fa-star", {
        message: "The star should be filled",
    });
    expect(".o_search_panel_section").toHaveCount(3);
    expect.verifySteps(["action_toggle_favorite"]);
    expect(".o_search_panel_section.o_search_panel_category:first header b:first").toHaveText(
        "FAVORITES"
    );
    await contains(".o_dashboard_star").click();
    expect(".o_dashboard_star").not.toHaveClass("fa-star", {
        message: "The star should not be filled",
    });
    expect.verifySteps(["action_toggle_favorite"]);
    expect(".o_search_panel_section").toHaveCount(2);
});

test("Global filter with same id is not shared between dashboards", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    serverData.models["spreadsheet.dashboard"].records.push({
        id: 790,
        name: "Spreadsheet dup. with Pivot",
        json_data: JSON.stringify(spreadsheetData),
        spreadsheet_data: JSON.stringify(spreadsheetData),
        dashboard_group_id: 1,
    });
    serverData.models["spreadsheet.dashboard.group"].records[0].published_dashboard_ids = [
        789, 790,
    ];
    await createSpreadsheetDashboard({ serverData });
    expect(".o_searchview_facet").toHaveCount(0);
    await contains(".o_spreadsheet_dashboard_action .dropdown-toggle").click();

    await contains(".o-autocomplete--input.o_input").click();
    expect(".o-filter-value .o_tag_badge_text").toHaveCount(0);
    await contains(".dropdown-item:first").click();
    expect(".o-filter-value .o_tag_badge_text").toHaveCount(1);

    await contains(".o-filter-values-footer .btn-primary").click();
    expect(".o_searchview_facet").toHaveCount(1);

    await contains(".o_search_panel li:last-child").click();
    expect(".o_searchview_facet").toHaveCount(0);
});

test("Search bar is not present if there is no global filters", async function () {
    const spreadsheetData = {
        globalFilters: [],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });

    expect(".o_sp_dashboard_search").toHaveCount(0);
});

test("Can add a new global filter from the search bar", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });

    await contains(".o_spreadsheet_dashboard_action .dropdown-toggle").click();

    expect(".o-autocomplete--input.o_input").toHaveCount(1);
    expect(".o-autocomplete--input.o_input").toHaveValue("");
    await contains(".o-autocomplete--input.o_input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    await contains(".o-filter-values-footer .btn-primary").click();

    expect(".o_searchview_facet").toHaveCount(1);
    expect(".o_searchview_facet .o_searchview_facet_label").toHaveText("Relation Filter");
    expect(".o_searchview_facet .o_facet_value").toHaveText("xphone");
});

test("Can open the dialog by clicking on a facet", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: { operator: "in", ids: [37] }, // xphone
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });

    expect(".o_searchview_facet").toHaveCount(1);
    await contains(".o_searchview_facet .o_searchview_facet_label ").click();
    expect(".o-filter-values").toHaveCount(1);
});

test("Can open the dialog by clicking on the search bar", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: { operator: "in", ids: [37] }, // xphone
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });

    await contains(".o_searchview input").click();
    expect(".o-filter-values").toHaveCount(1);
});

test("Changes of global filters are not dispatched while inside the dialog", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    const { model } = await createSpreadsheetDashboard({ serverData });

    expect(model.getters.getGlobalFilterValue("1")).toBe(undefined);

    await contains(".o_spreadsheet_dashboard_action .dropdown-toggle").click();

    await contains(".o-autocomplete--input.o_input").click();
    await contains(".o-autocomplete--dropdown-item").click();
    expect(model.getters.getGlobalFilterValue("1")).toBe(undefined);
    await contains(".o-filter-values-footer .btn-primary").click();
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ operator: "in", ids: [37] });
});

test("First global filter date is displayed as button", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: { operator: "in", ids: [37] },
            },
            {
                id: "2",
                type: "date",
                label: "Period",
                defaultValue: "this_year",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });
    expect(".o_sp_date_filter_button").toHaveCount(1);
    expect(".o_searchview_facet").toHaveCount(1);
});

test("No date buttons are displayed if there is no date filter", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });
    expect(".o_sp_date_filter_button").toHaveCount(0);
});

test("Unknown value for relation filter is displayed as inaccessible", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: { operator: "in", ids: [9999] }, // unknown product
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });
    expect(".o_searchview_facet").toHaveCount(1);
    expect(".o_searchview_facet .o_facet_value").toHaveText("Inaccessible/missing record ID");
});

describe("Quick search bar", () => {
    const productFilter = {
        id: "1",
        type: "relation",
        label: "Product",
        modelName: "product",
    };

    const selectionFilter = {
        id: "55",
        type: "selection",
        label: "Selection Filter",
        resModel: "res.currency",
        selectionField: "position",
    };

    test("Can quick search a string in a relational filter", async function () {
        const spreadsheetData = { globalFilters: [productFilter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("phone");
        expect(".o-dropdown-item.focus").toHaveText("Search Product for: phone");
        await press("Enter");

        const filterValue = model.getters.getGlobalFilterValue(productFilter.id);
        expect(filterValue).toEqual({ operator: "ilike", strings: ["phone"] });
    });

    test("Can quick search a string in a relational filter if a record was already selected", async function () {
        const filter = { ...productFilter, defaultValue: { operator: "in", ids: [37] } };
        const spreadsheetData = { globalFilters: [filter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("test");
        expect(".o-dropdown-item.focus").toHaveText("Search Product for: test");
        await press("Enter");

        const filterValue = model.getters.getGlobalFilterValue(productFilter.id);
        expect(filterValue).toEqual({ operator: "ilike", strings: ["test"] });
    });

    test("Can quick search a specific record in a relational filter", async function () {
        const spreadsheetData = { globalFilters: [productFilter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("x");
        expect(".o-dropdown-item.focus").toHaveText("Search Product for: x");
        await contains(".o-dropdown-item.focus .o_expand").click();

        const children = queryAll(".o-dropdown-item.o_indent");
        expect(children.map((el) => el.innerText)).toEqual(["xphone", "xpad"]);
        await contains(children[0]).click();

        const filterValue = model.getters.getGlobalFilterValue(productFilter.id);
        expect(filterValue).toEqual({ operator: "in", ids: [37] });
    });

    test("Can load more records in the quick search", async function () {
        for (let i = 0; i < 15; i++) {
            Product._records.push({ id: i, display_name: "name" + i });
        }
        const serverData = getServerData({ globalFilters: [productFilter] });
        await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("name");
        expect(".o-dropdown-item.focus").toHaveText("Search Product for: name");
        await contains(".o-dropdown-item.focus .o_expand").click();

        const children = queryAll(".o-dropdown-item.o_indent");
        expect(children.map((el) => el.innerText)).toEqual([
            ...range(9).map((i) => `name${i}`),
            "Load more",
        ]);
        await contains(children.at(-1)).click();

        expect(queryAllTexts(".o-dropdown-item.o_indent")).toEqual(
            range(15).map((i) => `name${i}`)
        );
    });

    test("Can quick search a string in a text filter", async function () {
        const spreadsheetData = { globalFilters: [{ id: "2", type: "text", label: "Text" }] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("phone");
        expect(".o-dropdown-item.focus").toHaveText("Search Text for: phone");
        await press("Enter");

        const filterValue = model.getters.getGlobalFilterValue("2");
        expect(filterValue).toEqual({ operator: "ilike", strings: ["phone"] });
    });

    test("Can quick search a string in a text filter with a range of allowed values", async function () {
        const spreadsheetData = {
            sheets: [{ id: "sh1", name: "Sh1", cells: { A1: "phone", A2: "tablet", A3: "table" } }],
            globalFilters: [
                {
                    id: "2",
                    type: "text",
                    label: "Text",
                    rangesOfAllowedValues: ["Sh1!A1:A5"],
                },
            ],
        };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("a");
        expect(".o-dropdown-item.focus").toHaveText("Search Text for: a");
        await press("ArrowRight");
        await animationFrame();

        const children = queryAll(".o-dropdown-item.o_indent");
        expect(children.map((el) => el.innerText)).toEqual(["tablet", "table"]);
        await contains(children[1]).click();

        const filterValue = model.getters.getGlobalFilterValue("2");
        expect(filterValue).toEqual({ operator: "ilike", strings: ["table"] });
    });

    test("Cannot search for a string that is not in rangesOfAllowedValues", async function () {
        const spreadsheetData = {
            sheets: [{ id: "sh1", name: "Sh1", cells: { A1: "phone", A2: "tablet", A3: "table" } }],
            globalFilters: [
                {
                    id: "2",
                    type: "text",
                    label: "Text",
                    rangesOfAllowedValues: ["Sh1!A1:A5"],
                },
            ],
        };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("desk");
        expect(".o-dropdown-item.focus").toHaveText("Search Text for: desk");
        await press("Enter");

        const filterValue = model.getters.getGlobalFilterValue("2");
        expect(filterValue).toEqual(undefined);
    });

    test("Can quick search a selection filter value", async function () {
        const spreadsheetData = { globalFilters: [selectionFilter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("a");
        expect(".o-dropdown-item.focus").toHaveText("Search Selection Filter for: a");
        await contains(".o-dropdown-item.focus .o_expand").click();

        const children = queryAll(".o-dropdown-item.o_indent");
        expect(children.map((el) => el.innerText)).toEqual(["A"]);
        await contains(children[0]).click();

        const filterValue = model.getters.getGlobalFilterValue(selectionFilter.id);
        expect(filterValue).toEqual({ operator: "in", selectionValues: ["after"] });
    });

    test("Date and numeric filters are not in the quick search results", async function () {
        const numericFilter = { id: "255", type: "numeric", label: "Numeric Filter" };
        const spreadsheetData = {
            globalFilters: [productFilter, THIS_YEAR_GLOBAL_FILTER, numericFilter, selectionFilter],
        };
        const serverData = getServerData(spreadsheetData);
        await createSpreadsheetDashboard({ serverData });

        await contains(".o_searchview_input").edit("phone");
        expect(queryAllTexts(".o-dropdown-item")).toEqual([
            "Search Product for: phone",
            "Search Selection Filter for: phone",
        ]);
    });

    test("Pressing backspace will remove the last facet", async function () {
        const filter = { ...productFilter, defaultValue: { operator: "in", ids: [37] } };
        const spreadsheetData = { globalFilters: [filter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });

        let filterValue = model.getters.getGlobalFilterValue(productFilter.id);
        expect(filterValue).toEqual({ operator: "in", ids: [37] });

        await contains(".o_searchview_input").focus();
        await press("Backspace");

        filterValue = model.getters.getGlobalFilterValue(productFilter.id);
        expect(filterValue).toEqual(undefined);
    });
});

describe("Filter list behavior in search bar", () => {
    async function setupDashboardWithFilter(globalFilter) {
        const spreadsheetData = { globalFilters: [globalFilter] };
        const serverData = getServerData(spreadsheetData);
        const { model } = await createSpreadsheetDashboard({ serverData });
        await toggleSearchBarMenu();
        return { model };
    }

    test("Can set a text filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "text",
            label: "Text Filter",
        });

        await contains(".o-filter-values select").select("not ilike");
        await contains(".o-filter-values .o-autocomplete input").edit("foo");
        await press("Enter");
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);

        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual({
            operator: "not ilike",
            strings: ["foo"],
        });
    });

    test("Can set a numeric filter value with basic operator", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "numeric",
            label: "Numeric Filter",
        });

        await contains(".o-filter-values select").select(">");
        await contains(".o-filter-values input").edit(1998);
        await press("Enter");
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
            message: "value is not directly set",
        });

        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual(
            { operator: ">", targetValue: 1998 },
            { message: "value is set" }
        );
    });

    test("Can set a numeric filter value with between operator", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "numeric",
            label: "Numeric Filter",
        });

        await contains(".o-filter-values select").select("between");
        const [minInput, maxInput] = document.querySelectorAll(".o-global-filter-numeric-value");
        expect([minInput, maxInput]).toHaveLength(2);
        await contains(minInput).edit(1);
        await contains(maxInput).edit(99);
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual(
            { operator: "between", minimumValue: 1, maximumValue: 99 },
            { message: "value is set" }
        );
    });

    test("Can set a relation filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "relation",
            modelName: "product",
            label: "Relation Filter",
        });

        await contains(".o-filter-values select").select("not in");
        await contains("input.o-autocomplete--input").click();
        await contains(".o-autocomplete--dropdown-item:first").click();
        expect(".o_tag").toHaveCount(1);

        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual(
            { operator: "not in", ids: [37] },
            { message: "value is set" }
        );

        await toggleSearchBarMenu();
        await contains(".o_tag .o_delete").click();
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    });

    test("Can remove a default relation filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "relation",
            modelName: "product",
            label: "Relation Filter",
            defaultValue: { operator: "in", ids: [37] },
        });
        expect(".o_tag").toHaveCount(1);

        await contains(".o_tag .o_delete").click();
        expect(".o_tag").toHaveCount(0);

        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    });

    test("Can change a boolean filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "boolean",
            label: "Boolean Filter",
        });
        expect(".o-filter-values select").toHaveValue("");

        await contains(".o-filter-values select").select("not set");
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual({ operator: "not set" });

        await toggleSearchBarMenu();
        await contains(".o-filter-values select").select("");
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    });

    test("Can set a date filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "date",
            label: "Date Filter",
        });

        await contains(".o-date-filter-input").click();
        await contains(".o-dropdown-item[data-id='last_7_days']").click();
        expect(".o-date-filter-input").toHaveValue("Last 7 Days");

        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual({
            period: "last_7_days",
            type: "relative",
        });
    });

    test("Readonly user can update a filter value", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "text",
            label: "Text Filter",
        });
        model.updateMode("readonly");

        await contains(".o-filter-values .o-autocomplete input").edit("foo");
        await press("Enter");
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42").strings).toEqual(["foo"], {
            message: "value is set",
        });
    });

    test("Can clear a filter value removing the values manually", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "text",
            label: "Text Filter",
            defaultValue: { operator: "ilike", strings: ["foo"] },
        });
        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(1);

        await contains(".o-filter-values .o-filter-item .o_tag .o_delete").click();
        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined, {
            message: "value is cleared",
        });
    });

    test("Can clear a filter value with the clear button", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "text",
            label: "Text Filter",
            defaultValue: { operator: "ilike", strings: ["foo"] },
        });
        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(1);

        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(1);
        await contains(".o-filter-values .o-filter-item .o-filter-clear button").click();
        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toBe(undefined);
    });

    test("clearing a filter value preserves the operator", async function () {
        const { model } = await setupDashboardWithFilter({
            id: "42",
            type: "text",
            label: "Text Filter",
            defaultValue: { operator: "ilike", strings: ["foo"] },
        });

        await contains(".o-filter-values select").select("starts with");
        await contains(".o-filter-values .o-filter-item .o_tag .o_delete").click();
        expect(".o-filter-values .o-filter-item .o_tag").toHaveCount(0);
        expect(".o-filter-values select").toHaveValue("starts with");

        await contains(".o-filter-values .o-filter-item .o-autocomplete input").edit("foo");
        await contains(".o-filter-values .o-filter-item .o-autocomplete input").press("Enter");
        await contains(".o-filter-values-footer .btn-primary").click();
        expect(model.getters.getGlobalFilterValue("42")).toEqual({
            operator: "starts with",
            strings: ["foo"],
        });
    });
});

describe("Favorite filters in search bar", () => {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);

    beforeEach(async () => {
        await createSpreadsheetDashboard({ serverData });
    });

    test("simple favorite menu rendering", async function () {
        await toggleSearchBarMenu();
        await toggleSaveFavorite();
        expect(`.o_add_favorite + .o_accordion_values input[type="text"]`).toHaveValue(
            "Spreadsheet with Pivot"
        );
        expect(`.o_add_favorite + .o_accordion_values input[type="checkbox"]`).toHaveCount(1);
        expect(`.o_add_favorite + .o_accordion_values .form-check label`).toHaveText(
            "Default filter"
        );
    });

    test("save favorite filters", async function () {
        onRpc("create", ({ args, route }) => {
            expect.step(route);
            const favoriteFilter = args[0][0];
            expect(favoriteFilter.name).toBe("aaa");
            expect(favoriteFilter.dashboard_id).toBe(789);
            expect(favoriteFilter.global_filters).toEqual({});
            expect(favoriteFilter.is_default).toBe(false);
            expect(favoriteFilter.user_ids).toEqual([7]);
            return [7];
        });

        expect.verifySteps([]);
        await toggleSaveFavorite();
        await editFavoriteName("aaa");
        await saveFavorite();
        expect.verifySteps(["/web/dataset/call_kw/spreadsheet.dashboard.favorite.filters/create"]);
    });

    test("save and edit favorite filters", async function () {
        onRpc("create", ({ args, route }) => {
            expect.step(route);
            const favoriteFilter = args[0][0];
            expect(favoriteFilter.name).toBe("aaa");
            return [7];
        });
        mockService("action", {
            doAction(action) {
                expect(action).toEqual({
                    context: {
                        form_view_ref:
                            "spreadsheet_dashboard.spreadsheet_dashboard_favorite_filters_view_edit_form",
                    },
                    res_id: 7,
                    res_model: "spreadsheet.dashboard.favorite.filters",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
                expect.step("Edit favorite");
            },
        });

        expect.verifySteps([]);
        await toggleSaveFavorite();
        await editFavoriteName("aaa");
        await saveAndEditFavorite();
        expect.verifySteps([
            "/web/dataset/call_kw/spreadsheet.dashboard.favorite.filters/create",
            "Edit favorite",
        ]);
    });
});
