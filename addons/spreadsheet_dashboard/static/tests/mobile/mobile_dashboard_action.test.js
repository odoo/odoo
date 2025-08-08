import { describe, expect, test } from "@odoo/hoot";
import { dblclick, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineSpreadsheetDashboardModels();

test("with no available dashboard", async () => {
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard"].records = [];
    serverData.models["spreadsheet.dashboard.group"].records = [];
    await createSpreadsheetDashboard({ serverData });
    expect(queryAllTexts`.o_mobile_dashboard`).toEqual(["No available dashboard"]);
});

test("double clicking on a figure doesn't open the side panel", async () => {
    const figure = {
        tag: "chart",
        height: 500,
        width: 500,
        col: 0,
        row: 0,
        offset: {
            x: 100,
            y: 100,
        },
        data: {
            chartId: "chartId",
            type: "line",
            dataSetsHaveTitle: false,
            dataSets: [{ dataRange: "A1" }],
            legendPosition: "top",
            verticalAxisPosition: "left",
            title: { text: "" },
        },
    };
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                figures: [{ ...figure, id: "figure1" }],
            },
        ],
    };
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard.group"].records = [
        {
            published_dashboard_ids: [789],
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
    await createSpreadsheetDashboard({ serverData });
    await contains(".o-chart-container").focus();
    await dblclick(".o-chart-container");
    await animationFrame();
    expect(".o-chart-container").toHaveCount(1);
    expect(".o-sidePanel").toHaveCount(0);
});

test("can switch dashboard", async () => {
    await createSpreadsheetDashboard();
    expect(".o_search_panel_summary").toHaveText("Dashboard CRM 1");
    await contains(".o_search_panel_current_selection").click();
    const dashboardElements = queryAll("section header.list-group-item", { root: document.body });
    expect(dashboardElements[0]).toHaveClass("active");
    expect(queryAllTexts(dashboardElements)).toEqual([
        "Dashboard CRM 1",
        "Dashboard CRM 2",
        "Dashboard Accounting 1",
    ]);
    await contains(dashboardElements[1]).click();
    expect(".o_search_panel_summary").toHaveText("Dashboard CRM 2");
});

test("can go back from dashboard selection", async () => {
    await createSpreadsheetDashboard();
    expect(".o_mobile_dashboard").toHaveCount(1);
    expect(".o_search_panel_summary").toHaveText("Dashboard CRM 1");
    await contains(".o_search_panel_current_selection").click();
    await contains(document.querySelector(".o_mobile_search_button")).click();
    expect(".o_search_panel_summary").toHaveText("Dashboard CRM 1");
});
