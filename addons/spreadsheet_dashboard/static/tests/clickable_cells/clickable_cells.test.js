import { describe, expect, test } from "@odoo/hoot";
import { click, queryAll, queryFirst } from "@odoo/hoot-dom";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { Partner } from "@spreadsheet/../tests/helpers/data";
import { fields } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("A link in a dashboard should be clickable", async () => {
    const data = {
        sheets: [
            {
                cells: { A1: "[Odoo](https://odoo.com)" },
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
                    A1: '=PIVOT.VALUE("1", "measure")',
                    A2: '=ODOO.LIST("1", 1, "name")',
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
                    A1: { content: '=PIVOT.VALUE("1", "probability", "bar", "false")' },
                    A2: { content: '=ODOO.LIST(1, 1, "foo")' },
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

test("list sorting clickable cell", async () => {
    Partner._fields.foo = fields.Integer({ sortable: true });
    Partner._fields.bar = fields.Boolean({ sortable: false });
    const data = {
        sheets: [
            {
                cells: {
                    A1: '=ODOO.LIST.HEADER(1, "foo")',
                    A2: '=ODOO.LIST(1, 1, "foo")',
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [],
                domain: [],
                model: "partner",
                orderBy: [],
            },
        },
    };
    const { model } = await createDashboardActionWithData(data);
    expect(".o-dashboard-clickable-cell .fa-sort").toHaveCount(1);

    await click(queryFirst(".o-dashboard-clickable-cell .sorting-icon"));
    expect(model.getters.getListDefinition(1).orderBy).toEqual([{ name: "foo", asc: true }]);
    await animationFrame();

    await click(queryFirst(".o-dashboard-clickable-cell .sorting-icon"));
    expect(model.getters.getListDefinition(1).orderBy).toEqual([{ name: "foo", asc: false }]);
    await animationFrame();

    await click(queryFirst(".o-dashboard-clickable-cell .sorting-icon"));
    expect(model.getters.getListDefinition(1).orderBy).toEqual([]);
});

test("list sort multiple fields", async () => {
    Partner._fields.foo = fields.Integer({ sortable: true });
    Partner._fields.bar = fields.Boolean({ sortable: true });
    const data = {
        sheets: [
            {
                cells: {
                    A1: '=ODOO.LIST.HEADER(1, "foo")',
                    A2: '=ODOO.LIST.HEADER(1, "bar")',
                },
            },
        ],
        lists: {
            1: {
                id: 1,
                columns: [],
                domain: [],
                model: "partner",
                orderBy: [],
            },
        },
    };
    const { model } = await createDashboardActionWithData(data);

    await click(queryAll(".o-dashboard-clickable-cell .sorting-icon")[0]);
    expect(model.getters.getListDefinition(1).orderBy).toEqual([{ name: "foo", asc: true }]);
    await animationFrame();

    await click(queryAll(".o-dashboard-clickable-cell .sorting-icon")[1]);
    expect(model.getters.getListDefinition(1).orderBy).toEqual([
        { name: "bar", asc: true },
        { name: "foo", asc: true },
    ]);

    await click(queryAll(".o-dashboard-clickable-cell .sorting-icon")[0]);
    expect(model.getters.getListDefinition(1).orderBy).toEqual([
        { name: "foo", asc: true },
        { name: "bar", asc: true },
    ]);
    await animationFrame();

    await click(queryAll(".o-dashboard-clickable-cell .sorting-icon")[0]);
    expect(model.getters.getListDefinition(1).orderBy).toEqual([
        { name: "foo", asc: false },
        { name: "bar", asc: true },
    ]);
    await animationFrame();

    await click(queryAll(".o-dashboard-clickable-cell .sorting-icon")[0]);
    expect(model.getters.getListDefinition(1).orderBy).toEqual([]);
    await animationFrame();
});
