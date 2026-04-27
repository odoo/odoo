import { before, expect, test, getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { contains, defineModels } from "@web/../tests/web_test_helpers";
import { mountSaleOrderSpreadsheetAction } from "./helpers/webclient_helpers";

import { selectCell } from "@spreadsheet/../tests/helpers/commands";

import { addSpreadsheetFieldSyncExtensionWithCleanUp } from "../src/bundle/field_sync/field_sync_extension_hook";
import { addFieldSync, deleteFieldSyncs } from "./helpers/commands";
import { defineSpreadsheetSaleModels } from "./helpers/data";
import { getFieldSync } from "./helpers/getters";

defineSpreadsheetSaleModels();
defineModels(mailModels);

before(() => {
    addSpreadsheetFieldSyncExtensionWithCleanUp();
});

test("display config", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("A1");
    expect(".o-sidePanelBody input[type=number]").toHaveValue(1);
    expect(".o_model_field_selector").toHaveText("Product uom qty");
});

test("update cell", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await contains(".o-selection-input input").edit("A2");
    expect(".o-selection-input input").toHaveValue("A2");
    expect(getFieldSync(model, "A1")).toBe(undefined);
    expect(getFieldSync(model, "A2")).not.toBe(undefined);
});

test("confirm with the same position", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await contains(".o-selection-input input").focus();
    await contains(".o-selection-ok").click();
    expect(".o-selection-input input").toHaveValue("A1");
    expect(getFieldSync(model, "A1")).not.toBe(undefined);
});

test("update cell by a range", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await contains(".o-selection-input input").focus();
    await animationFrame();
    await contains(".o-selection-input input").edit("A2:A3", { confirm: false });
    await contains(".o-selection-ok").click();
    expect(".o-selection-input input").toHaveValue("A2");
    expect(getFieldSync(model, "A1")).toBe(undefined);
    expect(getFieldSync(model, "A2")).not.toBe(undefined);
});

test("update cell with an invalid reference", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await contains(".o-selection-input input").edit("not a valid reference");
    expect(".o-selection-input input").toHaveValue("not a valid reference");
    expect(".o-selection-input input").toHaveClass("border-danger");
    expect(getFieldSync(model, "A1")).not.toBe(undefined);
});

test("update position", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await contains(".o-sidePanelBody input[type=number]").edit("9");
    expect(getFieldSync(model, "A1").indexInList).toBe(8);
});

test("update field", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    const position = { sheetId, col: 0, row: 0 };
    env.openSidePanel("FieldSyncSidePanel", { position });
    await animationFrame();
    expect(".o_model_field_selector").toHaveText("Product uom qty");
    await contains(".o_model_field_selector").click();
    await contains(
        ".o_model_field_selector_popover_item .o_model_field_selector_popover_item_name:contains(Qty delivered)"
    ).click();
    expect(".o_model_field_selector").toHaveText("Qty delivered");
    expect(getFieldSync(model, "A1").fieldName).toBe("qty_delivered");
});

test("open side panel in another position", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "B2", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    env.openSidePanel("FieldSyncSidePanel", { position: { sheetId, col: 0, row: 0 } });
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("A1");
    selectCell(model, "B2");
    env.openSidePanel("FieldSyncSidePanel", { position: { sheetId, col: 1, row: 1 } });
    await animationFrame();
    expect(".o-selection-input input").toHaveValue("B2");
});

test("side panel is closed when field sync is deleted", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    env.openSidePanel("FieldSyncSidePanel", { position: { sheetId, col: 0, row: 0 } });
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(1);
    deleteFieldSyncs(model, "A1");
    await animationFrame();
    expect(".o-sidePanel").toHaveCount(0);
});

test("side panel input value preserved on render", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    env.openSidePanel("FieldSyncSidePanel", { position: { sheetId, col: 0, row: 0 } });
    await animationFrame();
    const fixture = getFixture();
    const input = fixture.querySelector(".o-sidePanel input.o_input");
    input.focus();
    input.value = "10";
    await animationFrame();
    expect(input.value).toBe("10");
});

test("side panel saves input value on close", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const sheetId = model.getters.getActiveSheetId();
    env.openSidePanel("FieldSyncSidePanel", { position: { sheetId, col: 0, row: 0 } });
    await animationFrame();
    const fixture = getFixture();
    const input = fixture.querySelector(".o-sidePanel input.o_input");
    input.focus();
    input.value = "10";
    await contains(".o-sidePanelClose").click();
    await animationFrame();
    expect(getFieldSync(model, "A1").indexInList).toBe(9);
});
