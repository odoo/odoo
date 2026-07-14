import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import {
    defineActions,
    getService,
    mountWithCleanup,
    onRpc,
    mockService,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineActions([
    {
        id: 42,
        name: "Stock report",
        tag: "stock_report_generic",
        type: "ir.actions.client",
        context: {},
        params: {},
    },
]);
defineMailModels();

test("Rendering with no lines", async function () {
    onRpc("get_main_lines", () => []);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(42);
    expect(".o_stock_reports_page").toHaveText("No operation made on this lot.");
});

test("Traceability Report action contains correct url in context", async function () {
    onRpc("get_main_lines", () => [
        {
            id: 42,
            model: "stock.move.line",
            model_id: 42,
            parent_id: false,
            usage: "out",
            is_used: true,
            lot_name: "0001",
            lot_id: 1,
            reference: "WH/MO/00001",
            res_id: 4,
            res_model: "mrp.production",
            columns: [
                { name: "reference", value: "WH/MO/00001" },
                { name: "product", value: "Engine" },
                { name: "date", value: "08/07/2026 10:44:33 AM" },
                { name: "lot_name", value: "0000000010001" },
                { name: "location_source", value: "WH/Stock" },
                { name: "location_destination", value: "Production" },
                { name: "quantity", value: "1.00 Units" },
            ],
            level: 1,
            unfoldable: false,
        },
    ]);
    await mountWithCleanup(WebClient);
    mockService("action", {
        doAction(action) {
            const res = super.doAction(...arguments);
            if (action?.type === "ir.actions.client") {
                expect(action.context.url).toEqual(
                    "/stock/output_format/stock?active_id=:active_id&active_model=:active_model"
                );
            }
            return res;
        },
    });
    await getService("action").doAction(42);
    await click(".fa-level-up");
});
