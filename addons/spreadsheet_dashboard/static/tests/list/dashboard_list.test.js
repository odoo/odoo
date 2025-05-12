import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, fields, onRpc } from "@web/../tests/web_test_helpers";
import { stores } from "@odoo/o-spreadsheet";
import { createDashboardActionWithData } from "../helpers/dashboard_action";
import { Partner } from "@spreadsheet/../tests/helpers/data";

const { DelayedHoveredCellStore } = stores;

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("list sorting popover", async () => {
    Partner._fields.foo = fields.Integer({ sortable: true });
    Partner._fields.bar = fields.Boolean({ sortable: false });
    const data = {
        sheets: [
            {
                cells: {
                    A1: '=ODOO.LIST(1, 1, "foo")',
                    A2: '=ODOO.LIST(1, 1, "bar")',
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
    const { model, env } = await createDashboardActionWithData(data);
    const hoveredCellStore = env.getStore(DelayedHoveredCellStore);
    const sheetId = model.getters.getActiveSheetId();
    const A1 = { sheetId, col: 0, row: 0 };
    const A2 = { sheetId, col: 0, row: 1 };

    hoveredCellStore.hover(A1);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(1);

    await contains(".o-dashboard-menu").click();
    await contains(".o-menu-item .fa-sort-numeric-asc").click();
    expect(model.getters.getListDefinition("1").orderBy).toEqual([{ name: "foo", asc: true }]);
    await contains(".o-menu-item .fa-sort-numeric-desc").click();
    expect(model.getters.getListDefinition("1").orderBy).toEqual([{ name: "foo", asc: false }]);

    hoveredCellStore.hover(A2);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(0);
});

test("display list sorting popover when loaded", async () => {
    const data = {
        sheets: [
            {
                cells: {
                    A1: '=ODOO.LIST(1, 1, "foo")',
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
    const def = new Deferred();
    onRpc("partner", "fields_get", async ({ parent }) => {
        await def;
        return parent();
    });
    const { model, env } = await createDashboardActionWithData(data);
    const hoveredCellStore = env.getStore(DelayedHoveredCellStore);
    const sheetId = model.getters.getActiveSheetId();
    const A1 = { sheetId, col: 0, row: 0 };
    hoveredCellStore.hover(A1);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(0);
    def.resolve();
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(1);
});
