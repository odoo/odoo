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

const TEST_LINE_CHART_DATA = {
    type: "line",
    dataSetsHaveTitle: false,
    dataSets: [{ dataRange: "A1" }],
    legendPosition: "top",
    verticalAxisPosition: "left",
    title: { text: "" },
};

const TEST_SCORECARD_CHART_DATA = {
    type: "scorecard",
    title: { text: "test" },
    keyValue: "A1",
    background: "#fff",
    baselineMode: "absolute",
};

test("is empty with no figures", async () => {
    await createSpreadsheetDashboard();
    expect(".o_mobile_dashboard").toHaveCount(1);
    expect(".o_mobile_dashboard").toHaveText(
        "Only chart figures are displayed in small screens but this dashboard doesn't contain any"
    );
});

test("with no available dashboard", async () => {
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard"].records = [];
    serverData.models["spreadsheet.dashboard.group"].records = [];
    await createSpreadsheetDashboard({ serverData });
    expect(".o_mobile_dashboard").toHaveText("No available dashboard");
});

test("displays figures in first sheet", async () => {
    const figure = {
        tag: "chart",
        height: 500,
        width: 500,
        col: 0,
        row: 0,
        offset: { x: 100, y: 100 },
        data: TEST_LINE_CHART_DATA,
    };
    const spreadsheetData = {
        sheets: [
            { id: "sheet1", figures: [{ ...figure, id: "figure1" }] },
            { id: "sheet2", figures: [{ ...figure, id: "figure2" }] },
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
    expect(".o-chart-container").toHaveCount(1);
});

test("scorecards are placed two per row", async () => {
    const figure = {
        tag: "chart",
        height: 500,
        width: 500,
        offset: { x: 100, y: 100 },
        col: 0,
        row: 0,
    };
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                figures: [
                    { ...figure, id: "figure1", data: TEST_SCORECARD_CHART_DATA },
                    { ...figure, id: "figure2", data: TEST_SCORECARD_CHART_DATA },
                    { ...figure, id: "figure3", data: TEST_SCORECARD_CHART_DATA },
                    { ...figure, id: "figure4", data: TEST_LINE_CHART_DATA },
                ],
            },
        ],
    };
    const serverData = getDashboardServerData();
    serverData.models["spreadsheet.dashboard.group"].records = [
        { published_dashboard_ids: [789], id: 1, name: "Chart" },
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
    const figureRows = queryAll(".o_figure_row");
    expect(figureRows).toHaveLength(3);
    expect(figureRows[0].querySelectorAll(".o-scorecard")).toHaveLength(2);

    expect(figureRows[1].querySelectorAll(".o-scorecard")).toHaveLength(1);
    expect(figureRows[1].querySelectorAll(".o_empty_figure")).toHaveLength(1);

    expect(figureRows[2].querySelectorAll(".o-figure-canvas")).toHaveLength(1);
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
        data: TEST_LINE_CHART_DATA,
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
    expect(".o_search_panel_current_selection").toHaveText("Dashboard CRM 1");
    await contains(".o_search_panel_current_selection").click();
    const dashboardElements = queryAll("section header.list-group-item", { root: document.body });
    expect(dashboardElements[0]).toHaveClass("active");
    expect(queryAllTexts(dashboardElements)).toEqual([
        "Dashboard CRM 1",
        "Dashboard CRM 2",
        "Dashboard Accounting 1",
    ]);
    await contains(dashboardElements[1]).click();
    expect(".o_search_panel_current_selection").toHaveText("Dashboard CRM 2");
});

test("can go back from dashboard selection", async () => {
    await createSpreadsheetDashboard();
    expect(".o_mobile_dashboard").toHaveCount(1);
    expect(".o_search_panel_current_selection").toHaveText("Dashboard CRM 1");
    await contains(".o_search_panel_current_selection").click();
    await contains(document.querySelector(".o_mobile_search_button")).click();
    expect(".o_search_panel_current_selection").toHaveText("Dashboard CRM 1");
});
