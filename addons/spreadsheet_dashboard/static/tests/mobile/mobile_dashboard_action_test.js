/** @odoo-module */

import { click, getFixture } from "@web/../tests/helpers/utils";
import { createSpreadsheetDashboard } from "../utils/dashboard_action";
import { getDashboardServerData } from "../utils/data";

QUnit.module("spreadsheet_dashboard > Mobile Dashboard action");

QUnit.test("is empty with no figures", async (assert) => {
    await createSpreadsheetDashboard();
    const fixture = getFixture();
    assert.containsOnce(fixture, ".o_mobile_dashboard");
    const content = fixture.querySelector(".o_mobile_dashboard");
    assert.deepEqual(content.innerText.split("\n"), [
        "Dashboard CRM 1",
        "Only chart figures are displayed in small screens but this dashboard doesn't contain any",
    ]);
});

QUnit.test("with no available dashboard", async (assert) => {
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard"].records = [];
    serverData.models["spreadsheet.dashboard.group"].records = [];
    await createSpreadsheetDashboard({ serverData });
    const fixture = getFixture();
    const content = fixture.querySelector(".o_mobile_dashboard");
    assert.deepEqual(content.innerText, "No available dashboard");
});

QUnit.test("displays figures in first sheet", async (assert) => {
    const figure = {
        tag: "chart",
        height: 500,
        width: 500,
        x: 100,
        y: 100,
        data: {
            type: "line",
            dataSetsHaveTitle: false,
            dataSets: ["A1"],
            legendPosition: "top",
            verticalAxisPosition: "left",
            title: "",
        },
    };
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                figures: [{ ...figure, id: "figure1" }],
            },
            {
                id: "sheet2",
                figures: [{ ...figure, id: "figure2" }],
            },
        ],
    };
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard.group"].records = [
        {
            dashboard_ids: [789],
            id: 1,
            name: "Chart",
        },
    ];
    serverData.models["spreadsheet.dashboard"].records = [
        {
            id: 789,
            name: "Spreadsheet with chart figure",
            json_data: JSON.stringify(spreadsheetData),
            spreadsheet_data: JSON.stringify(spreadsheetData),
            dashboard_group_id: 1,
        },
    ];
    const fixture = getFixture();
    await createSpreadsheetDashboard({ serverData });
    assert.containsOnce(fixture, ".o-chart-container");
});

QUnit.test("can switch dashboard", async (assert) => {
    await createSpreadsheetDashboard();
    const fixture = getFixture();
    assert.strictEqual(
        fixture.querySelector(".o_search_panel_summary").innerText,
        "Dashboard CRM 1"
    );
    await click(fixture, ".o_search_panel_current_selection");
    const dashboardElements = [...document.querySelectorAll("section header.list-group-item")];
    assert.strictEqual(dashboardElements[0].classList.contains("active"), true);
    assert.deepEqual(
        dashboardElements.map((el) => el.innerText),
        ["Dashboard CRM 1", "Dashboard CRM 2", "Dashboard Accounting 1"]
    );
    await click(dashboardElements[1]);
    assert.strictEqual(
        fixture.querySelector(".o_search_panel_summary").innerText,
        "Dashboard CRM 2"
    );
});

QUnit.test("can go back from dashboard selection", async (assert) => {
    await createSpreadsheetDashboard();
    const fixture = getFixture();
    assert.containsOnce(fixture, ".o_mobile_dashboard");
    assert.strictEqual(
        fixture.querySelector(".o_search_panel_summary").innerText,
        "Dashboard CRM 1"
    );
    await click(fixture, ".o_search_panel_current_selection");
    await click(document, ".o_mobile_search_button");
    assert.strictEqual(
        fixture.querySelector(".o_search_panel_summary").innerText,
        "Dashboard CRM 1"
    );
});
