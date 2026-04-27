import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { defineModels, onRpc } from "@web/../tests/web_test_helpers";
import { x2ManyCommands } from "@web/core/orm_service";

import { mailModels } from "@mail/../tests/mail_test_helpers";

import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCellContent } from "@spreadsheet/../tests/helpers/getters";

import { helpers, stores } from "@odoo/o-spreadsheet";
import { addFieldSync } from "./helpers/commands";
import {
    defineSpreadsheetSaleModels,
    getSaleOrderSpreadsheetData,
    SaleOrderSpreadsheet,
} from "./helpers/data";
import { mountSaleOrderSpreadsheetAction } from "./helpers/webclient_helpers";

const { HighlightStore, HoveredCellStore } = stores;
const { toZone } = helpers;

defineSpreadsheetSaleModels();
defineModels(mailModels);

test("write on sale order when leaving action", async () => {
    const orderId = 1;
    onRpc("sale.order", "write", ({ args }) => {
        const [orderIds, vals] = args;
        expect(orderIds).toEqual([orderId]);
        expect(vals).toEqual({
            order_line: [
                x2ManyCommands.update(1, {
                    product_uom_qty: 1000,
                }),
            ],
        });
        expect.step("write-sale-order");
        return true;
    });
    const { model } = await mountSaleOrderSpreadsheetAction();
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "1000");
    await click("button:contains(Save in sale.order,1)");
    await animationFrame();
    expect.verifySteps(["write-sale-order"]);
});

test("don't write on sale order with no order_id param", async () => {
    onRpc("sale.order", "write", () => {
        expect.step("write-sale-order");
    });
    const spreadsheetId = 1;
    SaleOrderSpreadsheet._records = [
        {
            id: spreadsheetId,
            name: "My sale order spreadsheet",
            spreadsheet_data: JSON.stringify(getSaleOrderSpreadsheetData()),
            order_id: false,
        },
    ];
    const { model } = await mountSaleOrderSpreadsheetAction({ spreadsheetId });
    addFieldSync(model, "A1", "product_uom_qty", 0);
    setCellContent(model, "A1", "1000");
    expect("button:contains(Write to sale.order,1)").toHaveCount(0);
});

test("global filter initialized with orderId", async () => {
    const { model } = await mountSaleOrderSpreadsheetAction();
    const [filter] = model.getters.getGlobalFilters();
    expect(model.getters.getGlobalFilterValue(filter.id)).toEqual([1]);
});

test("auto resize list columns", async () => {
    onRpc("sale.order.spreadsheet", "join_spreadsheet_session", () => {
        const data = getSaleOrderSpreadsheetData();
        const commands = [
            {
                type: "RE_INSERT_ODOO_LIST",
                sheetId: data.sheets[0].id,
                col: 0,
                row: 0,
                id: "1",
                linesNumber: 20,
                columns: [{ name: "product_uom_qty", type: "float" }],
            },
        ];
        return {
            name: "my spreadsheet",
            data,
            isReadonly: false,
            revisions: [
                {
                    serverRevisionId: "START_REVISION",
                    nextRevisionId: "abcd",
                    version: "1",
                    type: "REMOTE_REVISION",
                    commands,
                },
            ],
        };
    });
    const { model } = await mountSaleOrderSpreadsheetAction();
    const sheetId = model.getters.getActiveSheetId();
    expect(getCellContent(model, "A1")).toBe('=ODOO.LIST.HEADER(1,"product_uom_qty")');
    expect(model.getters.getHeaderSize(sheetId, "COL", 0)).not.toBe(96);
    expect(model.getters.getHeaderSize(sheetId, "COL", 1)).toBe(96); // default width
});

test("hover field sync highlights matching list formulas", async () => {
    const { model, env } = await mountSaleOrderSpreadsheetAction();
    const hoverStore = env.getStore(HoveredCellStore);
    const highlightStore = env.getStore(HighlightStore);
    addFieldSync(model, "B1", "product_uom_qty", 0);
    setCellContent(model, "A1", '=ODOO.LIST(1,1,"product_uom_qty")');
    expect(highlightStore.highlights).toHaveLength(0);
    hoverStore.hover({ col: 1, row: 0 });
    expect(highlightStore.highlights).toEqual([
        {
            zone: toZone("A1"),
            color: "#875A7B",
            sheetId: model.getters.getActiveSheetId(),
        },
    ]);

    // with computed list args
    setCellContent(model, "A1", "=ODOO.LIST(A2, A3, A4)");
    expect(highlightStore.highlights).toHaveLength(0);
    setCellContent(model, "A2", "1");
    setCellContent(model, "A3", "1");
    setCellContent(model, "A4", "product_uom_qty");
    hoverStore.hover({ col: 1, row: 0 });
    expect(highlightStore.highlights).toEqual([
        {
            zone: toZone("A1"),
            color: "#875A7B",
            sheetId: model.getters.getActiveSheetId(),
        },
    ]);
});
