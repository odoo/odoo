import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { addGlobalFilter, selectCell, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import { getCell, getCellValue, getEvaluatedGrid } from "@spreadsheet/../tests/helpers/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";

describe.current.tags("headless");
defineSpreadsheetModels();

const { topbarMenuRegistry } = spreadsheet.registries;
const { toZone } = spreadsheet.helpers;

test("Re-insert a pivot with a global filter should re-insert the full pivot", async function () {
    const { model, env } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
    });
    await addGlobalFilter(model, {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
    });
    selectCell(model, "A6");
    const reinsertPivotPath = ["data", "reinsert_static_pivot", "reinsert_static_pivot_1"];
    await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
    await animationFrame();
    expect(getCellValue(model, "B6")).toBe(getCellValue(model, "B1"));
});

test("re-insert PIVOT day_of_week with order from the server", async function () {
    const serverData = getBasicServerData();
    serverData.models.partner.records = [
        { probability: 1, date: "2025-02-17" }, // Monday
        { probability: 2, date: "2025-02-18" }, // Tuesday
        { probability: 3, date: "2025-02-19" }, // Wednesday
        { probability: 4, date: "2025-02-20" }, // Thursday
        { probability: 5, date: "2025-02-21" }, // Friday
        { probability: 6, date: "2025-02-22" }, // Saturday
        { probability: 7, date: "2025-02-23" }, // Sunday
    ];
    const { model, env, pivotId } = await createSpreadsheetWithPivot({
        serverData,
        arch: /* xml */ `
            <pivot>
                <field name="date" interval="day" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    model.dispatch("UPDATE_LOCALE", {
        locale: {
            ...model.getters.getLocale(),
            weekStart: 1, // Monday
        },
    });
    updatePivot(model, pivotId, {
        rows: [{ fieldName: "date", granularity: "day_of_week" }],
    });
    model.dispatch("CLEAR_CELLS", {
        target: [toZone("A1:F100")],
        sheetId: model.getters.getActiveSheetId(),
    });
    const reinsertPivotPath = ["data", "reinsert_static_pivot", "reinsert_static_pivot_1"];
    await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
    await animationFrame();
    // in an ideal world, it would be ordered according to the locale (starting at 1)
    expect(getEvaluatedGrid(model, "A1:A9")).toEqual([
        [null],
        [null],
        ["Sunday"],
        ["Monday"],
        ["Tuesday"],
        ["Wednesday"],
        ["Thursday"],
        ["Friday"],
        ["Saturday"],
    ]);
    expect(getCell(model, "A3").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",7)');
    expect(getCell(model, "A4").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",1)');
    expect(getCell(model, "A5").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",2)');
    expect(getCell(model, "A6").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",3)');
    expect(getCell(model, "A7").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",4)');
    expect(getCell(model, "A8").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",5)');
    expect(getCell(model, "A9").content).toBe('=PIVOT.HEADER(1,"date:day_of_week",6)');
});
