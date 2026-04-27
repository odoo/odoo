import { before, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { Model } from "@odoo/o-spreadsheet";

import { x2ManyCommands } from "@web/core/orm_service";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import {
    addColumns,
    addRows,
    autofill,
    copy,
    cut,
    deleteColumns,
    paste,
    redo,
    setCellContent,
    undo,
} from "@spreadsheet/../tests/helpers/commands";
import { getCellContent } from "@spreadsheet/../tests/helpers/getters";
import { defineModels, onRpc } from "@web/../tests/web_test_helpers";
import { addSpreadsheetFieldSyncExtensionWithCleanUp } from "../src/bundle/field_sync/field_sync_extension_hook";
import {
    addFieldSync,
    createSaleOrderSpreadsheetModel,
    deleteFieldSyncs,
} from "./helpers/commands";
import { SaleOrderLine, defineSpreadsheetSaleModels } from "./helpers/data";
import { getFieldSync } from "./helpers/getters";

describe.current.tags("headless");

defineModels(mailModels);
defineSpreadsheetSaleModels();

before(() => {
    addSpreadsheetFieldSyncExtensionWithCleanUp();
});

test("add a field sync", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const fieldSync = getFieldSync(model, "A1");
    expect(fieldSync).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    undo(model);
    expect(getFieldSync(model, "A1")).toBe(undefined);
    redo(model);
    expect(getFieldSync(model, "A1")).toEqual(fieldSync);
});

test("delete a field sync", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const fieldSync = getFieldSync(model, "A1");
    deleteFieldSyncs(model, "A1");
    expect(getFieldSync(model, "A1")).toBe(undefined);
    undo(model);
    expect(getFieldSync(model, "A1")).toBe(fieldSync);
    redo(model);
    expect(getFieldSync(model, "A1")).toBe(undefined);
});

test("export/import a field sync", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const data = model.exportData();
    expect(data.sheets[0].fieldSyncs["A1"]).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    const newModel = new Model(data);
    expect(getFieldSync(newModel, "A1")).toEqual(getFieldSync(model, "A1"));
});

test("can't add same field sync twice", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    const result = addFieldSync(model, "A1", "product_uom_qty", 0);
    expect(result.isSuccessful).toBe(false);
});

test("can't delete field sync that doesn't exist", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    expect(deleteFieldSyncs(model, "A1").isSuccessful).toBe(false);
});

test("field sync is moved when column is added before", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addColumns(model, "before", "A", 1);
    expect(getFieldSync(model, "A1")).toBe(undefined);
    expect(getFieldSync(model, "B1")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
});

test("field sync is moved when row is added before", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "A2", "product_uom_qty", 1);
    addRows(model, "before", 0, 1);
    expect(getFieldSync(model, "A1")).toBe(undefined);
    expect(getFieldSync(model, "A2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "A3")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 1,
        fieldName: "product_uom_qty",
    });
});

test("field sync is deleted when column is removed", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    deleteColumns(model, ["A"]);
    expect(getFieldSync(model, "A1")).toBe(undefined);
    expect(model.getters.getAllFieldSyncs().size).toBe(0);
});

test("x2many commands when the cell is empty", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    expect(getCellContent(model, "A1")).toBe("");
    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [],
        errors: [],
    });
});

test("x2many commands when the cell is a number", async () => {
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "111");
    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [
            x2ManyCommands.update(42, {
                product_uom_qty: 111,
            }),
        ],
        errors: [],
    });
});

test("x2many commands with field sync position bigger than formula", async () => {
    SaleOrderLine._records = [{ id: 42 }, { id: 43 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "A2", "product_uom_qty", 1); // has a matching record but not loaded
    addFieldSync(model, "A3", "product_uom_qty", 2); // doesn't have a matching record
    setCellContent(model, "A1", "111");
    setCellContent(model, "A2", "112");
    setCellContent(model, "B1", '=ODOO.LIST(1, 1, "order_id")');
    await animationFrame();
    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [
            x2ManyCommands.update(42, {
                product_uom_qty: 111,
            }),
            x2ManyCommands.update(43, {
                product_uom_qty: 112,
            }),
        ],
        errors: [],
    });
});

test("load order lines list only once", async () => {
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    SaleOrderLine._records = [{ id: 42 }, { id: 43 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "A2", "product_uom_qty", 1);
    setCellContent(model, "A1", "111");
    setCellContent(model, "A2", "112");
    setCellContent(model, "B1", '=ODOO.LIST(1, 1, "order_id")');
    setCellContent(model, "B1", '=ODOO.LIST(1, 2, "order_id")');
    await animationFrame();
    expect.verifySteps(["web_search_read"]);
    await model.getters.getFieldSyncX2ManyCommands();
    expect.verifySteps([]);

    // add a field sync beyond the loaded records
    addFieldSync(model, "A3", "product_uom_qty", 2);
    await model.getters.getFieldSyncX2ManyCommands();
    expect.verifySteps(["web_search_read"]);
});

test("x2many commands on 2 fields", async () => {
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "A2", "qty_delivered", 0);
    setCellContent(model, "A1", "111");
    setCellContent(model, "A2", "222");
    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [
            x2ManyCommands.update(42, {
                product_uom_qty: 111,
                qty_delivered: 222,
            }),
        ],
        errors: [],
    });
});

test("x2many commands when the cell is an error", async () => {
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "=1/0");
    expect((await model.getters.getFieldSyncX2ManyCommands()).errors).toEqual([
        'The value of A1 (#DIV/0!) can\'t be used for field "Product uom qty". It should be a number.',
    ]);
});

test("x2many commands text value on a numeric field", async () => {
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "Hello");
    expect((await model.getters.getFieldSyncX2ManyCommands()).errors).toEqual([
        'The value of A1 (Hello) can\'t be used for field "Product uom qty". It should be a number.',
    ]);
});

test("x2many commands numeric value on a text field", async () => {
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "name", 0);
    setCellContent(model, "A1", "30%");
    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [
            x2ManyCommands.update(42, {
                name: "30%",
            }),
        ],
        errors: [],
    });
});

test("x2many commands with not enough records in the list", async () => {
    // only one record
    SaleOrderLine._records = [{ id: 42 }];
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "111");

    // doesn't match any record in the list
    addFieldSync(model, "A2", "product_uom_qty", 1);
    setCellContent(model, "A2", "222");

    expect(await model.getters.getFieldSyncX2ManyCommands()).toEqual({
        commands: [
            x2ManyCommands.update(42, {
                product_uom_qty: 111,
            }),
        ],
        errors: [],
    });
});

test("auto fill down increments position", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    autofill(model, "A1", "A3");
    expect(getFieldSync(model, "A2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 1,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "A3")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 2,
        fieldName: "product_uom_qty",
    });
});

test("auto fill up decrements position", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A3", "product_uom_qty", 2);
    autofill(model, "A3", "A1");
    expect(getFieldSync(model, "A2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 1,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "A1")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
});

test("auto fill up stops at 0", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A3", "product_uom_qty", 1);
    autofill(model, "A3", "A1");
    expect(getFieldSync(model, "A2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "A1")).toBe(undefined);
});

test("auto fill right copies", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    autofill(model, "A1", "B1");
    expect(getFieldSync(model, "B1")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
});

test("auto fill left copies", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    autofill(model, "B1", "A1");
    expect(getFieldSync(model, "A1")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
});

test("copy-paste below", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    copy(model, "B1");
    paste(model, "B2");
    expect(getFieldSync(model, "B2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 1,
        fieldName: "product_uom_qty",
    });
});

test("copy-paste up", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B3", "product_uom_qty", 1);
    copy(model, "B3");
    paste(model, "B2");
    paste(model, "B1");
    expect(getFieldSync(model, "B2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "B1")).toBe(undefined);
});

test("copy-paste horizontally", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    copy(model, "B1");
    paste(model, "A1");
    paste(model, "C1");
    const fieldSync = getFieldSync(model, "B1");
    expect(getFieldSync(model, "A1")).toEqual(fieldSync);
    expect(getFieldSync(model, "C1")).toEqual(fieldSync);
});

test("copy-paste horizontally and vertically", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    copy(model, "B1");
    paste(model, "C2");
    expect(getFieldSync(model, "C2")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 1,
        fieldName: "product_uom_qty",
    });
});

test("copy-paste zone", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    addFieldSync(model, "B2", "product_uom_qty", 1);
    copy(model, "B1:B2");
    paste(model, "B3");
    expect(getFieldSync(model, "B3")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 2,
        fieldName: "product_uom_qty",
    });
    expect(getFieldSync(model, "B4")).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 3,
        fieldName: "product_uom_qty",
    });
});

test("cut-paste", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B1", "product_uom_qty", 0);
    const originalFieldSync = getFieldSync(model, "B1");
    cut(model, "B1");
    paste(model, "B3");
    expect(getFieldSync(model, "B3")).toBe(originalFieldSync);
    expect(getFieldSync(model, "B1")).toBe(undefined);
});

test("can't delete main sale order line list", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    const result = model.dispatch("REMOVE_ODOO_LIST", {
        listId: model.getters.getMainSaleOrderLineList().id,
    });
    expect(result.isSuccessful).toBe(false);
});

test("can't delete main sale order global filter", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    const [filter] = model.getters.getGlobalFilters();
    const result = model.dispatch("REMOVE_GLOBAL_FILTER", { id: filter.id });
    expect(result.isSuccessful).toBe(false);
});

test("duplicated field sync error", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    addFieldSync(model, "A2", "product_uom_qty", 0);
    expect((await model.getters.getFieldSyncX2ManyCommands()).errors).toEqual([]);
    setCellContent(model, "A1", "111");
    expect((await model.getters.getFieldSyncX2ManyCommands()).errors).toEqual([]);
    setCellContent(model, "A2", "789");
    expect((await model.getters.getFieldSyncX2ManyCommands()).errors).toEqual([
        "Multiple cells are updating the same field of the same record! Unable to determine which one to choose: A1, A2",
    ]);
});
