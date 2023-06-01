/** @odoo-module */

import {
    getFixture,
    click,
    legacyExtraNextTick,
    nextTick,
    editInput,
} from "@web/../tests/helpers/utils";
import { getDashboardServerData } from "../utils/data";
import { getBasicData, getBasicListArchs } from "@spreadsheet/../tests/utils/data";
import { createSpreadsheetDashboard } from "../utils/dashboard_action";

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
            raw: JSON.stringify(spreadsheetData),
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
            if (method === "search_read" && model === "spreadsheet.dashboard.group") {
                return [];
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
    await createSpreadsheetDashboard({
        mockRPC: function (route, args) {
            if (
                args.model === "spreadsheet.dashboard" &&
                ((args.method === "read" && args.args[0][0] === 2 && args.args[1][0] === "raw") ||
                    // this is not correct from a module dependency POV but it's required for the test
                    // to pass when `spreadsheet_dashboard_edition` module is installed
                    (args.method === "join_spreadsheet_session" && args.args[0] === 2))
            ) {
                throw new Error("Bip");
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
        await legacyExtraNextTick();
        assert.containsOnce(fixture, ".o_list_view");
        await click(document.body.querySelector(".o_back_button"));
        await legacyExtraNextTick();
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
                    rangeType: "year",
                    defaultValue: {},
                    defaultsToCurrentPeriod: true,
                    pivotFields: {},
                },
            ],
        };
        const serverData = getServerData(spreadsheetData);
        const fixture = getFixture();
        await createSpreadsheetDashboard({ serverData });
        const year = fixture.querySelector(".o_cp_top_right input.o_datepicker_input");
        const this_year = luxon.DateTime.local().year;
        assert.equal(year.value, String(this_year));
        const input = fixture.querySelector(
            "input.o_datepicker_input.o_input.datetimepicker-input"
        );
        await click(input);
        await editInput(input, null, String(this_year - 1));
        await nextTick();

        assert.equal(year.value, String(this_year - 1));
        assert.containsOnce(fixture, ".o_cp_top_right .fa-times");
        await click(fixture.querySelector(".o_cp_top_right .fa-times"));

        assert.containsNone(fixture, ".o_cp_top_right .fa-times");
        assert.equal(year.value, "");
    }
);
