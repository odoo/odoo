import { describe, expect, test } from "@odoo/hoot";
import { dblclick, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
defineSpreadsheetDashboardModels();

function getServerData(spreadsheetData) {
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
    return serverData;
}

test("is empty with no figures", async () => {
    await createSpreadsheetDashboard();
    expect(".o_mobile_dashboard").toHaveCount(1);
    expect(".o_mobile_dashboard").toHaveText(
        "Dashboard CRM 1\n" +
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
        x: 100,
        y: 100,
        data: {
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
            {
                id: "sheet2",
                figures: [{ ...figure, id: "figure2" }],
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });
    expect(".o-chart-container").toHaveCount(1);
});

test("clicking on a chart navigates to its linked Odoo menu", async () => {
    const fakeActionService = {
        doAction: async (actionRequest, options = {}) => {
            if (actionRequest === "menuAction") {
                expect.step("redirect to odoo menu");
            }
        },
    };
    const figure = {
        tag: "chart",
        data: {
            type: "line",
            dataSets: [{ dataRange: "A1" }],
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
        chartOdooMenusReferences: {
            figure1: "documents_spreadsheet.test.menu",
        },
    };
    const serverData = getServerData(spreadsheetData);
    serverData.menus = {
        1: {
            id: 1,
            xmlid: "documents_spreadsheet.test.menu",
            actionID: "menuAction",
        },
    };
    await createSpreadsheetDashboard({ serverData });
    mockService("action", fakeActionService);

    await contains(".o-chart-container").click();
    expect.verifySteps(["redirect to odoo menu"]);
});

test("double clicking on a figure doesn't open the side panel", async () => {
    const figure = {
        tag: "chart",
        height: 500,
        width: 500,
        x: 100,
        y: 100,
        data: {
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
    const serverData = getServerData(spreadsheetData);
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
