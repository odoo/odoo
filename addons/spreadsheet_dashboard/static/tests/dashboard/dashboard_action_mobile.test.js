import { describe, expect, test, getFixture } from "@odoo/hoot";
import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
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

test("Search input is not focusable in mobile", async () => {
    const productFilter = {
        id: "1",
        type: "relation",
        label: "Product",
        modelName: "product",
    };
    const spreadsheetData = { globalFilters: [productFilter] };
    const serverData = getServerData(spreadsheetData);
    await createSpreadsheetDashboard({ serverData });

    await contains(".o_searchview_input").click();

    const input = getFixture().querySelector(".o_searchview_input");
    expect(document.activeElement).not.toBe(input);
    expect(".o_bottom_sheet .o-filter-values").toHaveCount(1);
});
