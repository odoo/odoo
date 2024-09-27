import { describe, expect, getFixture, onError as onErrorHoot, test } from "@odoo/hoot";
import { click, pointerDown, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, getMockEnv, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
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
    const fixture = getFixture();
    await contains(fixture.querySelector(".o_spreadsheet_dashboard_search_panel button")).click();
    expect(".o_spreadsheet_dashboard_search_panel").toHaveCount(0);
    expect(fixture.querySelector(".o_search_panel_sidebar").textContent).toBe(
        "Container 1 / Dashboard CRM 1"
    );
    await contains(fixture.querySelector(".o_search_panel_sidebar button")).click();
    expect(".o_search_panel_sidebar").toHaveCount(0);
    expect(".o_spreadsheet_dashboard_search_panel").toHaveCount(1);
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
    const active = getFixture().querySelector(".o_search_panel li.active");
    expect(active.innerText).toBe("Dashboard Accounting 1");
});

test("can switch spreadsheet", async () => {
    await createSpreadsheetDashboard();
    const fixture = getFixture();
    const spreadsheets = fixture.querySelectorAll(".o_search_panel li");
    expect(spreadsheets[0].className.includes("active")).toBe(true);
    expect(spreadsheets[1].className.includes("active")).toBe(false);
    expect(spreadsheets[2].className.includes("active")).toBe(false);
    await contains(spreadsheets[1]).click();
    expect(spreadsheets[0].className.includes("active")).toBe(false);
    expect(spreadsheets[1].className.includes("active")).toBe(true);
    expect(spreadsheets[2].className.includes("active")).toBe(false);
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
    const fixture = getFixture();
    expect(".o_search_panel li").toHaveCount(0, {
        message: "It should not display any spreadsheet",
    });
    expect(fixture.querySelector(".dashboard-loading-status").innerText).toBe(
        "No available dashboard",
        { message: "It should display no dashboard message" }
    );
});

test("display error message", async () => {
    onErrorHoot((ev) => ev.preventDefault());
    await createSpreadsheetDashboard({
        mockRPC: function (route, args) {
            if (
                args.model === "spreadsheet.dashboard" &&
                args.method === "get_readonly_dashboard" &&
                args.args[0] === 2
            ) {
                const error = new RPCError();
                error.data = {};
                throw error;
            }
        },
    });
    const fixture = getFixture();
    const spreadsheets = fixture.querySelectorAll(".o_search_panel li");
    expect(".o-spreadsheet").toHaveCount(1, { message: "It should display the spreadsheet" });
    await contains(spreadsheets[1]).click();
    expect(".o_spreadsheet_dashboard_action .dashboard-loading-status.error").toHaveCount(1, {
        message: "It should display an error",
    });
    await contains(spreadsheets[0]).click();
    expect(".o-spreadsheet").toHaveCount(1, { message: "It should display the spreadsheet" });
    expect(".o_renderer .error").toHaveCount(0, { message: "It should not display an error" });
});

test("load dashboard that doesn't exist", async () => {
    onErrorHoot((ev) => ev.preventDefault());
    await createSpreadsheetDashboard({
        spreadsheetId: 999,
    });
    expect(".o_spreadsheet_dashboard_action .dashboard-loading-status.error").toHaveCount(1, {
        message: "It should display an error",
    });
});

test("Last selected spreadsheet is kept when go back from breadcrumb", async function () {
    const spreadsheetData = {
        version: 16,
        sheets: [
            {
                id: "sheet1",
                cells: { A1: { content: `=PIVOT.VALUE("1", "probability")` } },
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
    const fixture = getFixture();
    await createSpreadsheetDashboard({ serverData });
    await contains(".o_search_panel li:last-child").click();
    await contains(".o-dashboard-clickable-cell").click();
    expect(".o_list_view").toHaveCount(1);
    await contains(document.body.querySelector(".o_back_button")).click();
    expect(fixture.querySelector(".o_search_panel li:last-child")).toHaveClass("active");
});

test("Can clear filter date filter value that defaults to current period", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "Date Filter",
                rangeType: "fixedPeriod",
                defaultValue: "this_year",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    const fixture = getFixture();
    await createSpreadsheetDashboard({ serverData });
    const year = fixture.querySelector(".o_control_panel_actions input.o_datetime_input");
    const this_year = luxon.DateTime.local().year;
    expect(year.value).toBe(String(this_year));
    const input = fixture.querySelector("input.o_datetime_input");
    await contains(input).click();
    await contains(input).edit(String(this_year - 1));
    await animationFrame();

    expect(year.value).toBe(String(this_year - 1));
    expect(".o_control_panel_actions .fa-times").toHaveCount(1);
    await contains(fixture.querySelector(".o_control_panel_actions .fa-times")).click();

    expect(".o_control_panel_actions .fa-times").toHaveCount(0);
    expect(year.placeholder).toBe("Select year...");
});

test("Can delete record tag in the filter by hitting Backspace", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: [37],
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    const fixture = getFixture();
    await createSpreadsheetDashboard({ serverData });
    const filter = fixture.querySelector(".o_control_panel_actions div.o_multi_record_selector");
    const autoCompleteInput = filter.querySelector(".o-autocomplete--input.o_input");
    expect(filter.querySelectorAll(".o_tag").length).toBe(1);

    await pointerDown(autoCompleteInput);
    await press("Backspace");
    await animationFrame();
    expect(filter.querySelectorAll(".o_tag").length).toBe(0);
});

test("share dashboard from dashboard view", async function () {
    const target = getFixture();
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
    expect(target.querySelector(".spreadsheet_share_dropdown")?.innerText).toBe(
        "Generating sharing link"
    );
    def.resolve();
    await animationFrame();
    expect.verifySteps(["dashboard_shared", "share url copied"]);
    expect(target.querySelector(".o_field_CopyClipboardChar").innerText).toBe(
        "localhost:8069/share/url/132465"
    );
    await contains(".fa-clone").click();
    expect.verifySteps(["share url copied"]);
});

test("Changing filter values will create a new share", async function () {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "Date Filter",
                rangeType: "fixedPeriod",
                defaultValue: "this_year",
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    const target = getFixture();
    let counter = 0;
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: (url) => {},
    });
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
    expect(target.querySelector(".o_field_CopyClipboardChar").innerText).toBe(
        `localhost:8069/share/url/1`
    );

    await contains("i.fa-share-alt").click(); // close share dropdown

    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(target.querySelector(".o_field_CopyClipboardChar").innerText).toBe(
        `localhost:8069/share/url/1`
    );

    await contains("i.fa-share-alt").click();
    const year = target.querySelector(".o_control_panel_actions input.o_datetime_input");
    const this_year = luxon.DateTime.local().year;
    expect(year.value).toBe(String(this_year));
    const input = target.querySelector("input.o_datetime_input");
    await contains(input).click();
    await contains(input).edit(String(this_year - 1));
    await animationFrame();

    await contains("i.fa-share-alt").click();
    await animationFrame();
    expect(target.querySelector(".o_field_CopyClipboardChar")?.innerText).toBe(
        `localhost:8069/share/url/2`
    );
});

test("Clicking 'Edit' icon navigates to dashboard edit view", async function () {
    patchWithCleanup(odoo, { debug: true });
    const action = {
        type: "ir.actions.client",
        tag: "action_edit_dashboard",
        params: {
            spreadsheet_id: 1,
        },
    };
    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (args.method === "action_edit_dashboard" && args.model === "spreadsheet.dashboard") {
                expect.step("action_edit_dashboard");
                return action;
            }
        },
    });
    const env = getMockEnv();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("doAction");
            expect(action.params.spreadsheet_id).toBe(1);
            expect(action.tag).toBe("action_edit_dashboard");
        },
    });
    await click(".o_edit_dashboard");
    await animationFrame();
    expect.verifySteps(["action_edit_dashboard", "doAction"]);
});

test("User without edit permissions does not see the 'Edit' option on the dashboard (Debug mode ON)", async function () {
    patchWithCleanup(odoo, { debug: true });
    onRpc("has_group", async (route, args) => {
        return false;
    });
    await createSpreadsheetDashboard();
    expect(".o_edit_dashboard").toHaveCount(0);
});

test("User with edit permissions sees the 'Edit' option on the dashboard (Debug mode ON)", async function () {
    patchWithCleanup(odoo, { debug: true });
    onRpc("has_group", async (route, args) => {
        return true;
    });
    await createSpreadsheetDashboard();
    expect(
        getFixture().querySelector(".o_search_panel_category_value .o_edit_dashboard")
    ).toHaveCount(1);
});

test("User with edit permissions does not see the 'Edit' option on the dashboard (Debug mode OFF)", async function () {
    patchWithCleanup(odoo, { debug: false });
    onRpc("has_group", async (route, args) => {
        return true;
    });
    await createSpreadsheetDashboard();
    expect(".o_edit_dashboard").toHaveCount(0);
});
