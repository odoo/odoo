/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getFixture } from "@web/../tests/helpers/utils";
import { getDashboardServerData } from "../utils/data";
import { createSpreadsheetDashboard } from "../utils/dashboard_action";
import { getBasicData } from "@spreadsheet/../tests/utils/data";

const { Model } = spreadsheet;

async function createDashboardWithModel(model) {
    return createDashboardWithData(model.exportData());
}

async function createDashboardWithData(spreadsheetData) {
    const serverData = getDashboardServerData();
    const json = JSON.stringify(spreadsheetData);
    const dashboard = serverData.models["spreadsheet.dashboard"].records[0];
    dashboard.raw = json;
    dashboard.json_data = json;
    serverData.models = {
        ...serverData.models,
        ...getBasicData(),
    };
    await createSpreadsheetDashboard({ serverData, spreadsheetId: dashboard.id });
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
    const model = new Model(data, { mode: "dashboard" });
    const target = await createDashboardWithModel(model);
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
    const model = new Model(data, { mode: "dashboard" });
    const target = await createDashboardWithModel(model);
    assert.containsNone(target, ".o-dashboard-clickable-cell");
});

QUnit.test("pivot/list formulas should be clickable", async (assert) => {
    const data = {
        sheets: [
            {
                cells: {
                    A1: { content: '=ODOO.PIVOT(1,"probability")' },
                    A2: { content: '=ODOO.LIST(1, 1, "foo")' },
                },
            },
        ],
        pivots: {
            1: {
                id: 1,
                colGroupBys: [],
                domain: [],
                measures: [{ field: "probability", operator: "avg" }],
                model: "partner",
                rowGroupBys: [],
                context: {},
                fieldMatching: {},
            },
        },
        lists: {
            1: {
                id: 1,
                columns: ["foo", "contact_name"],
                domain: [],
                model: "partner",
                orderBy: [],
                context: {},
                fieldMatching: {},
            },
        },
    };
    const target = await createDashboardWithData(data);
    assert.containsN(target, ".o-dashboard-clickable-cell", 2);
});
