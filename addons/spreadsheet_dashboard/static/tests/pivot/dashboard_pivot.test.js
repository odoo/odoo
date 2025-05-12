import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { insertPivotInSpreadsheet } from "@spreadsheet/../tests/helpers/pivot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";
import { stores } from "@odoo/o-spreadsheet";

const { DelayedHoveredCellStore } = stores;

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("display sorting popover", async () => {
    const { model, env } = await createSpreadsheetDashboard();
    model.updateMode("normal");
    await insertPivotInSpreadsheet(model, "1", {
        arch: /*xml*/ `
            <pivot>
                <field name="foo" type="measure"/>
                <field name="product_id" type="row"/>
                <field name="bar" type="col"/>
            </pivot>`,
    });
    const hoveredCellStore = env.getStore(DelayedHoveredCellStore);
    const sheetId = model.getters.getActiveSheetId();
    const A1 = { sheetId, col: 0, row: 0 };
    const A2 = { sheetId, col: 0, row: 1 };
    const A3 = { sheetId, col: 0, row: 2 };

    // positional argument
    setCellContent(model, "A1", '=PIVOT.VALUE(1,"foo:sum", "#product_id", 1)');

    // static argument
    setCellContent(model, "A2", '=PIVOT.VALUE(1,"foo:sum", "product_id", 1)');

    // col field
    setCellContent(model, "A3", '=PIVOT.VALUE(1,"foo:sum", "#bar", 1)');

    model.updateMode("dashboard");

    hoveredCellStore.hover(A1);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(1);

    hoveredCellStore.hover(A2);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(0);

    hoveredCellStore.hover(A3);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(0);
});

test("don't display sorting popover with error", async () => {
    const { model, env } = await createSpreadsheetDashboard();
    model.updateMode("normal");
    await insertPivotInSpreadsheet(model, "1", {
        arch: /*xml*/ `
            <pivot>
                <field name="foo" type="measure"/>
                <field name="product_id" type="row"/>
                <field name="bar" type="col"/>
            </pivot>`,
    });
    const hoveredCellStore = env.getStore(DelayedHoveredCellStore);
    const sheetId = model.getters.getActiveSheetId();
    const A1 = { sheetId, col: 0, row: 0 };
    setCellContent(model, "A1", '=PIVOT.VALUE(1,"foo:sum", 0/0, 0/0)');
    model.updateMode("dashboard");
    hoveredCellStore.hover(A1);
    await animationFrame();
    expect(".o-dashboard-menu").toHaveCount(0);
});

test("clicking the sorting popover sorts pivot", async () => {
    const { model, env } = await createSpreadsheetDashboard();
    model.updateMode("normal");
    await insertPivotInSpreadsheet(model, "1", {
        arch: /*xml*/ `
            <pivot>
                <field name="foo" type="measure"/>
                <field name="product_id" type="row"/>
                <field name="bar" type="col"/>
            </pivot>`,
    });
    const hoveredCellStore = env.getStore(DelayedHoveredCellStore);
    const sheetId = model.getters.getActiveSheetId();
    const A1 = { sheetId, col: 0, row: 0 };
    setCellContent(model, "A1", '=PIVOT.VALUE(1,"foo:sum", "#product_id", 1,"bar",TRUE)');
    model.updateMode("dashboard");
    hoveredCellStore.hover(A1);
    await animationFrame();
    await click(".o-dashboard-menu");
    expect(model.getters.getPivotCoreDefinition("1").sortedColumn).toBe(undefined);
    await contains(".o-menu-item .fa-sort-numeric-asc").click();
    const pivot = model.getters.getPivotCoreDefinition("1");
    expect(pivot.sortedColumn).toEqual({
        measure: "foo:sum",
        order: "asc",
        domain: [{ field: "bar", value: true, type: "boolean" }],
    });
});
