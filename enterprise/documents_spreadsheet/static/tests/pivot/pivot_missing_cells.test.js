import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { registries } from "@odoo/o-spreadsheet";
import { redo, selectCell, undo } from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { contains } from "@web/../tests/web_test_helpers";

const { topbarMenuRegistry } = registries;

const insertPivotCellPath = ["data", "reinsert_pivot_cell", "reinsert_pivot_cell_1"];

import {
    defineDocumentSpreadsheetModels,
    getBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { getCellFormula, getCell } from "@spreadsheet/../tests/helpers/getters";
import { animationFrame } from "@odoo/hoot-dom";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

let fixture;

beforeEach(() => {
    fixture = getFixture();
});

test("Open pivot dialog and insert a value, with UNDO/REDO", async () => {
    const { model, env } = await createSpreadsheetFromPivotView();
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    expect("table.o_pivot_html_renderer").toHaveCount(1);
    const element = fixture.querySelectorAll(".o_pivot_html_renderer tr th")[1];
    await contains(element).click();
    expect(getCellFormula(model, "D8")).toBe(getCellFormula(model, "B1"));
    undo(model);
    expect(getCell(model, "D8")).toBe(undefined);
    redo(model);
    expect(getCellFormula(model, "D8")).toBe(getCellFormula(model, "B1"));
});

test("pivot dialog with row date field (day)", async function (assert) {
    const { env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                    <pivot>
                        <field name="date" interval="day" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    const firstRowHeader = fixture.querySelectorAll(".o_pivot_html_renderer tr th")[3];
    expect(firstRowHeader).toHaveText("14 Apr 2016");
});

test("pivot dialog with col date field (day)", async function (assert) {
    const { env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                    <pivot>
                        <field name="date" interval="day" type="col"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    const firstRowHeader = fixture.querySelectorAll(".o_pivot_html_renderer tr th")[1];
    expect(firstRowHeader).toHaveText("14 Apr 2016");
});

test("Insert missing value modal can show only the values not used in the current sheet", async () => {
    const { model, env } = await createSpreadsheetFromPivotView();
    const missingValue = getCellFormula(model, "B3");
    selectCell(model, "B3");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    expect("table.o_pivot_html_renderer th").toHaveCount(4);
    await contains(".o_missing_value").click();
    expect(getCellFormula(model, "D8")).toBe(missingValue);
});

test("Insert missing pivot value with two level of grouping", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                        <pivot string="Partners">
                            <field name="foo" type="col"/>
                            <field name="bar" type="row"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    selectCell(model, "B5");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    expect("table.o_pivot_html_renderer td").toHaveCount(1);
    expect("table.o_pivot_html_renderer th").toHaveCount(4);
});

test("Insert missing value modal can show only the values not used in the current sheet with multiple levels", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="foo" type="col"/>
                        <field name="product_id" type="col"/>
                        <field name="bar" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    const missingValue = getCellFormula(model, "C4");
    selectCell(model, "C4");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    selectCell(model, "J10");
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    expect("table.o_pivot_html_renderer th").toHaveCount(5);
    await contains(".o_missing_value").click();
    expect(getCellFormula(model, "J10")).toEqual(missingValue);
});

test("Insert missing pivot value give the focus to the grid hidden input when model is closed", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="foo" type="col"/>
                        <field name="bar" type="row"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    selectCell(model, "D8");
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    const element = fixture.querySelectorAll(".o_pivot_html_renderer tr th")[1];
    await contains(element).click();
    const gridComposerEl = document.body.querySelector(".o-grid div.o-composer");
    expect(document.activeElement).toBe(gridComposerEl);
});

test("One col header as missing value should be displayed", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                        <pivot string="Partners">
                            <field name="foo" type="col"/>
                            <field name="bar" type="row"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    selectCell(model, "B1");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
});

test("One row header as missing value should be displayed", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                        <pivot string="Partners">
                            <field name="foo" type="col"/>
                            <field name="bar" type="row"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    selectCell(model, "A3");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
});

test("A missing col in the total measures with a pivot of two GB of cols", async () => {
    const { model, env } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                    <pivot string="Partners">
                        <field name="bar" type="col"/>
                        <field name="product_id" type="col"/>
                        <field name="probability" type="measure"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    selectCell(model, "F4");
    model.dispatch("DELETE_CONTENT", {
        sheetId: model.getters.getActiveSheetId(),
        target: model.getters.getSelectedZones(),
    });
    await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
    await animationFrame();
    await contains("input[name='missing_values']").click();
    await animationFrame();
    expect("table.o_pivot_html_renderer .o_missing_value").toHaveCount(1);
    expect("table.o_pivot_html_renderer th").toHaveCount(5);
});
