/** @odoo-module */

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { getDashboardServerData } from "../utils/data";
import { createSpreadsheetDashboard } from "../utils/dashboard_action";
import { getBasicData } from "@spreadsheet/../tests/utils/data";

async function createDashboardActionWithData(data) {
    const serverData = getDashboardServerData();
    const json = JSON.stringify(data);
    const dashboard = serverData.models["spreadsheet.dashboard"].records[0];
    dashboard.spreadsheet_data = json;
    dashboard.json_data = json;
    serverData.models = {
        ...serverData.models,
        ...getBasicData(),
    };
    await createSpreadsheetDashboard({ serverData, spreadsheetId: dashboard.id });
    await nextTick();
    return getFixture();
}

QUnit.module("spreadsheet_dashboard > clickable cells");

QUnit.test("A link in a dashboard should be clickable", async (assert) => {
    const data = {
        sheets: [
            {
                cells: { A1: { content: "[Odoo](https://odoo.com)" } },
            },
        ],
    };
    const target = await createDashboardActionWithData(data);
    assert.containsOnce(target, ".o-dashboard-clickable-cell");
});

QUnit.test("Invalid pivot/list formulas should not be clickable", async (assert) => {
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content: `=ODOO.PIVOT("1", "measure")` },
                    A2: { content: `=ODOO.LIST("1", 1, "name")` },
                },
            },
        ],
    };
    const target = await createDashboardActionWithData(data);
    assert.containsNone(target, ".o-dashboard-clickable-cell");
});

QUnit.test("pivot/list formulas should be clickable", async (assert) => {
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content: `=ODOO.PIVOT("1", "probability", "bar", "false")` },
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
    const target = await createDashboardActionWithData(data);
    assert.containsN(target, ".o-dashboard-clickable-cell", 2);
});
