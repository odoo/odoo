import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { stores, helpers } from "@odoo/o-spreadsheet";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { addGlobalFilter, setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { makeStore, makeStoreWithModel } from "@spreadsheet/../tests/helpers/stores";

const { ClickableCellsStore } = stores;
const { toZone } = helpers;

describe.current.tags("headless");

defineSpreadsheetDashboardModels();

test("apply style to the row with list formula", async () => {
    const { store, model } = await makeStore(ClickableCellsStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: [],
    });
    setCellContent(model, "A1", '=ODOO.LIST(1, 1, "product_id")');
    setCellContent(model, "B1", '=ODOO.LIST(1, 1, "foo")');
    setCellContent(model, "C1", '=ODOO.LIST(1, 1, "bar")');
    await animationFrame();
    store.hoverClickableCell({ col: 1, row: 0 });
    const sheetId = model.getters.getActiveSheetId();
    expect(store.hoverStyles.get({ sheetId, col: 0, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 2, row: 0 })).toEqual({ fillColor: "#0000000D" });
});

test("merges are transparent when styling the list row", async () => {
    const { store, model } = await makeStore(ClickableCellsStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: [],
    });
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("ADD_MERGE", {
        target: [toZone("A1:B1")],
        sheetId,
    });
    setCellContent(model, "A1", '=ODOO.LIST(1, 1, "product_id")');
    setCellContent(model, "C1", '=ODOO.LIST(1, 1, "bar")');
    await animationFrame();
    store.hoverClickableCell({ col: 2, row: 0 });
    expect(store.hoverStyles.get({ sheetId, col: 0, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 2, row: 0 })).toEqual({ fillColor: "#0000000D" });
});

test("don't apply style to other lists", async () => {
    const { store, model } = await makeStore(ClickableCellsStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: [],
    });
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: [],
    });
    setCellContent(model, "A1", '=ODOO.LIST(2, 1, "product_id")');
    setCellContent(model, "B1", '=ODOO.LIST(1, 1, "foo")');
    setCellContent(model, "C1", '=ODOO.LIST(2, 1, "bar")');
    await animationFrame();
    store.hoverClickableCell({ col: 1, row: 0 });
    const sheetId = model.getters.getActiveSheetId();
    expect(store.hoverStyles.has({ sheetId, col: 0, row: 0 })).toBe(false);
    expect(store.hoverStyles.has({ sheetId, col: 1, row: 0 })).toBe(true);
    expect(store.hoverStyles.has({ sheetId, col: 2, row: 0 })).toBe(false);
});

test("apply style to adjacent pivot value and header", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="bar" type="col"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const { store } = makeStoreWithModel(model, ClickableCellsStore);
    store.hoverClickableCell({ col: 2, row: 2 });
    const sheetId = model.getters.getActiveSheetId();
    expect(store.hoverStyles.get({ sheetId, col: 0, row: 2 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 2 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 2, row: 2 })).toEqual({
        fillColor: "#0000000D",
        textColor: "#017E84",
    });
});

test("merges are transparent when styling the pivot row", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="bar" type="col"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const { store } = makeStoreWithModel(model, ClickableCellsStore);
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("CLEAR_CELLS", {
        sheetId,
        target: [toZone("A1:F10")],
    });
    model.dispatch("ADD_MERGE", {
        target: [toZone("A1:B1")],
        sheetId,
    });
    setCellContent(model, "A1", '=PIVOT.HEADER(1,"#product_id",1)');
    setCellContent(model, "C1", '=PIVOT.VALUE(1,"probability:avg","#product_id", 1)');
    store.hoverClickableCell({ col: 2, row: 0 });
    expect(store.hoverStyles.get({ sheetId, col: 0, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 0 })).toEqual({ fillColor: "#0000000D" });
    expect(store.hoverStyles.get({ sheetId, col: 2, row: 0 })).toEqual({
        fillColor: "#0000000D",
        textColor: "#017E84",
    });
});

test("row header matching global filter has a different background", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="bar" type="col"/>
                <field name="product_id" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const [pivotId] = model.getters.getPivotIds();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Product",
            modelName: "product",
        },
        {
            pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
        }
    );
    const { store } = makeStoreWithModel(model, ClickableCellsStore);
    store.hoverClickableCell({ col: 0, row: 2 });
    const sheetId = model.getters.getActiveSheetId();
    expect(store.hoverStyles.get({ sheetId, col: 0, row: 2 }).fillColor).toBe("#0000001A");
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 2 }).fillColor).toBe("#0000000D");
});

test("col header matching global filter has a different background", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="bar" type="row"/>
                <field name="product_id" type="col"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const [pivotId] = model.getters.getPivotIds();
    await addGlobalFilter(
        model,
        {
            id: "42",
            type: "relation",
            label: "Product",
            modelName: "product",
        },
        {
            pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
        }
    );
    const { store } = makeStoreWithModel(model, ClickableCellsStore);
    store.hoverClickableCell({ col: 2, row: 0 });
    const sheetId = model.getters.getActiveSheetId();
    expect(store.hoverStyles.has({ sheetId, col: 0, row: 0 })).toBe(false);
    expect(store.hoverStyles.get({ sheetId, col: 1, row: 0 }).fillColor).toBe("#0000000D");
    expect(store.hoverStyles.get({ sheetId, col: 2, row: 0 }).fillColor).toBe("#0000001A");
    expect(store.hoverStyles.get({ sheetId, col: 3, row: 0 }).fillColor).toBe("#0000000D");
});
