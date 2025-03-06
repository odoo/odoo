import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { stores } from "@odoo/o-spreadsheet";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { makeStore, makeStoreWithModel } from "@spreadsheet/../tests/helpers/stores";

const { ClickableCellsStore } = stores;

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
    expect(store.hoverStyles.has({ sheetId, col: 0, row: 0 })).toBe(true);
    expect(store.hoverStyles.has({ sheetId, col: 1, row: 0 })).toBe(true);
    expect(store.hoverStyles.has({ sheetId, col: 2, row: 0 })).toBe(true);
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

test.only("pivooooot", async () => {
    const { model } = await createSpreadsheetWithPivot({
        arch: /* xml */ `
            <pivot>
                <field name="bar" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
    });
    const { store } = makeStoreWithModel(model, ClickableCellsStore);
    store.hoverClickableCell({ col: 2, row: 2 });
});
