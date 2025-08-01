import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { RPCError } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";

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
    onRpc(
        "/spreadsheet/dashboard/data/2",
        () => {
            const error = new RPCError();
            error.data = {};
            throw error;
        },
        { pure: true }
    );
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
    expect(".spreadsheet_share_dropdown").toHaveText("Generating sharing link");
    def.resolve();
    await animationFrame();
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
    expect(".o_dashboard_star").toHaveClass("fa-star favorite_button_enabled", {
        message: "The star should be filled",
    });
    expect(".o_search_panel_section").toHaveCount(3);
    expect.verifySteps(["action_toggle_favorite"]);
    expect(".o_search_panel_section.o_search_panel_category:first header b:first").toHaveText(
        "FAVORITES"
    );
    await contains(".o_dashboard_star").click();
    expect(".o_dashboard_star").not.toHaveClass("fa-star favorite_button_enabled", {
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
    await contains(".o_searchview_facet").click();
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

    await contains(".o_searchview").click();
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
