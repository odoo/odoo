/** @odoo-module */

import {
    getFixture,
    click,
    nextTick,
    editInput,
    makeDeferred,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { getDashboardServerData } from "../utils/data";
import { getBasicData, getBasicListArchs } from "@spreadsheet/../tests/utils/data";
import { createSpreadsheetDashboard } from "../utils/dashboard_action";
import { keyDown } from "@spreadsheet/../tests/utils/ui";
import { RPCError } from "@web/core/network/rpc_service";
import { errorService } from "@web/core/errors/error_service";
import { registry } from "@web/core/registry";

QUnit.module("spreadsheet_dashboard > Dashboard > Dashboard action");

function getServerData(spreadsheetData) {
    const serverData = getDashboardServerData();
    serverData.models = {
        ...serverData.models,
        ...getBasicData(),
    };
    serverData.views = getBasicListArchs();
    serverData.models["spreadsheet.dashboard.group"].records = [
        {
            dashboard_ids: [789],
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

QUnit.test("display available spreadsheets", async (assert) => {
    await createSpreadsheetDashboard();
    assert.containsN(getFixture(), ".o_search_panel section", 2);
    assert.containsN(getFixture(), ".o_search_panel li", 3);
});

QUnit.test("display the active spreadsheet", async (assert) => {
    await createSpreadsheetDashboard();
    assert.containsOnce(
        getFixture(),
        ".o_search_panel li.active",
        "It should have one active element"
    );
    assert.containsOnce(getFixture(), ".o-spreadsheet", "It should display the spreadsheet");
});

QUnit.test("load action with specific dashboard", async (assert) => {
    await createSpreadsheetDashboard({ spreadsheetId: 3 });
    const active = getFixture().querySelector(".o_search_panel li.active");
    assert.strictEqual(active.innerText, "Dashboard Accounting 1");
});

QUnit.test("can switch spreadsheet", async (assert) => {
    await createSpreadsheetDashboard();
    const fixture = getFixture();
    const spreadsheets = fixture.querySelectorAll(".o_search_panel li");
    assert.ok(spreadsheets[0].className.includes("active"));
    assert.notOk(spreadsheets[1].className.includes("active"));
    assert.notOk(spreadsheets[2].className.includes("active"));
    await click(spreadsheets[1]);
    assert.notOk(spreadsheets[0].className.includes("active"));
    assert.ok(spreadsheets[1].className.includes("active"));
    assert.notOk(spreadsheets[2].className.includes("active"));
});

QUnit.test("display no dashboard message", async (assert) => {
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
    assert.containsNone(fixture, ".o_search_panel li", "It should not display any spreadsheet");
    assert.strictEqual(
        fixture.querySelector(".dashboard-loading-status").innerText,
        "No available dashboard",
        "It should display no dashboard message"
    );
});

QUnit.test("display error message", async (assert) => {
    registry.category("services").add("error", errorService);
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
    assert.containsOnce(fixture, ".o-spreadsheet", "It should display the spreadsheet");
    await click(spreadsheets[1]);
    assert.containsOnce(
        fixture,
        ".o_spreadsheet_dashboard_action .dashboard-loading-status.error",
        "It should display an error"
    );
    await click(spreadsheets[0]);
    assert.containsOnce(fixture, ".o-spreadsheet", "It should display the spreadsheet");
    assert.containsNone(fixture, ".o_renderer .error", "It should not display an error");
});

QUnit.test("load dashboard that doesn't exist", async (assert) => {
    registry.category("services").add("error", errorService);
    await createSpreadsheetDashboard({
        spreadsheetId: 999,
    });
    const fixture = getFixture();
    assert.containsOnce(
        fixture,
        ".o_spreadsheet_dashboard_action .dashboard-loading-status.error",
        "It should display an error"
    );
});

QUnit.test(
    "Last selected spreadsheet is kept when go back from breadcrumb",
    async function (assert) {
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: { A1: { content: `=PIVOT("1", "probability")` } },
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
        await click(fixture, ".o_search_panel li:last-child");
        await click(fixture, ".o-dashboard-clickable-cell");
        assert.containsOnce(fixture, ".o_list_view");
        await click(document.body.querySelector(".o_back_button"));
        assert.hasClass(fixture.querySelector(".o_search_panel li:last-child"), "active");
    }
);

QUnit.test(
    "Can clear filter date filter value that defaults to current period",
    async function (assert) {
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
        assert.equal(year.value, String(this_year));
        const input = fixture.querySelector("input.o_datetime_input");
        await click(input);
        await editInput(input, null, String(this_year - 1));
        await nextTick();

        assert.equal(year.value, String(this_year - 1));
        assert.containsOnce(fixture, ".o_control_panel_actions .fa-times");
        await click(fixture.querySelector(".o_control_panel_actions .fa-times"));

        assert.containsNone(fixture, ".o_control_panel_actions .fa-times");
        assert.equal(year.placeholder, "Select year...");
    }
);

QUnit.test("Can delete record tag in the filter by hitting Backspace", async function (assert) {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: [37],
                automaticDefaultValue: true,
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    const fixture = getFixture();
    await createSpreadsheetDashboard({ serverData });
    const filter = fixture.querySelector(".o_control_panel_actions div.o_multi_record_selector");
    const autoCompleteInput = filter.querySelector(".o-autocomplete--input.o_input");
    assert.equal(filter.querySelectorAll(".o_tag").length, 1);

    autoCompleteInput.focus();
    await keyDown({ key: "Backspace" });
    assert.equal(filter.querySelectorAll(".o_tag").length, 0);
});

QUnit.test("share dashboard from dashboard view", async function (assert) {
    const target = getFixture();
    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (url) => {
                    assert.step("share url copied");
                    assert.strictEqual(url, "localhost:8069/share/url/132465");
                },
            },
        },
    });
    const def = makeDeferred();
    await createSpreadsheetDashboard({
        mockRPC: async function (route, args) {
            if (args.method === "action_get_share_url") {
                await def;
                assert.step("dashboard_shared");
                assert.strictEqual(args.model, "spreadsheet.dashboard.share");
                return "localhost:8069/share/url/132465";
            }
        },
    });
    assert.strictEqual(target.querySelector(".spreadsheet_share_dropdown"), null);
    await click(target, "i.fa-share-alt");
    assert.equal(
        target.querySelector(".spreadsheet_share_dropdown")?.innerText,
        "Generating sharing link"
    );
    def.resolve();
    await nextTick();
    assert.verifySteps(["dashboard_shared", "share url copied"]);
    assert.strictEqual(
        target.querySelector(".o_field_CopyClipboardChar").innerText,
        "localhost:8069/share/url/132465"
    );
    await click(target, ".fa-clipboard");
    assert.verifySteps(["share url copied"]);
});

QUnit.test("Changing filter values will create a new share", async function (assert) {
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
    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (url) => {},
            },
        },
    });
    await createSpreadsheetDashboard({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "action_get_share_url") {
                return `localhost:8069/share/url/${++counter}`;
            }
        },
    });
    await click(target, "i.fa-share-alt");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_field_CopyClipboardChar").innerText,
        `localhost:8069/share/url/1`
    );

    await click(target, "i.fa-share-alt"); // close share dropdown

    await click(target, "i.fa-share-alt");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_field_CopyClipboardChar").innerText,
        `localhost:8069/share/url/1`
    );

    await click(target, "i.fa-share-alt");
    const year = target.querySelector(".o_control_panel_actions input.o_datetime_input");
    const this_year = luxon.DateTime.local().year;
    assert.equal(year.value, String(this_year));
    const input = target.querySelector("input.o_datetime_input");
    await click(input);
    await editInput(input, null, String(this_year - 1));
    await nextTick();

    await click(target, "i.fa-share-alt");
    await nextTick();
    assert.strictEqual(
        target.querySelector(".o_field_CopyClipboardChar")?.innerText,
        `localhost:8069/share/url/2`
    );
});
