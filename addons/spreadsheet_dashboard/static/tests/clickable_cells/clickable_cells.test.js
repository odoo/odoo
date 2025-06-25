import { describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    SpreadsheetDashboard,
    defineSpreadsheetDashboardModels,
} from "@spreadsheet_dashboard/../tests/helpers/data";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

async function createDashboardActionWithData(data) {
    const json = JSON.stringify(data);
    const dashboard = SpreadsheetDashboard._records[0];
    dashboard.spreadsheet_data = json;
    dashboard.json_data = json;
    await createSpreadsheetDashboard({ spreadsheetId: dashboard.id });
    await animationFrame();
    return getFixture();
}

test("A link in a dashboard should be clickable", async () => {
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[Odoo](https://odoo.com)" } },
            },
        ],
    };
    await createDashboardActionWithData(data);
    expect(".o-dashboard-clickable-cell").toHaveCount(1);
});

test("Invalid pivot/list formulas should not be clickable", async () => {
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content: `=PIVOT.VALUE("1", "measure")` },
                    A2: { content: `=ODOO.LIST("1", 1, "name")` },
                },
            },
        ],
    };
    await createDashboardActionWithData(data);
    expect(".o-dashboard-clickable-cell").toHaveCount(0);
});

test("pivot/list formulas should be clickable", async () => {
    const data = {
        version: 16,
        sheets: [
            {
                cells: {
                    A1: { content: `=PIVOT.VALUE("1", "probability", "bar", "false")` },
                    A2: { content: `=ODOO.LIST(1, 1, "foo")` },
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: ["foo"],
                domain: [],
                model: "partner",
                orderBy: [],
            },
        },
        pivots: {
            1: {
                id: 1,
                colGroupBys: ["foo"],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: ["bar"],
                context: {},
            },
        },
    };
    await createDashboardActionWithData(data);
    expect(".o-dashboard-clickable-cell").toHaveCount(2);
});
