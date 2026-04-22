import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineActions, getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { queryAll } from "@odoo/hoot-dom";
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";

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

test("ForecastedDetails - merges consecutive lines with same move_in and product", async () => {
    const props = {
        docs: {
            precision: 2,
            product: {
                57: {
                    uom: "Units",
                    qty: { in: 0.0, out: 0.0 },
                    draft_picking_qty: { in: 0.0, out: 0.0 },
                    draft_purchase_qty: { in: 0.0, out: 0.0 },
                },
            },
            lines: [
                {
                    product: { id: 57, display_name: "josv" },
                    quantity: 1,
                    move_in: { id: 70 },
                    receipt_date: "04/22/2026",
                    uom_id: { display_name: "Units" },
                    is_late: false,
                    document_in: { _name: "purchase.order", id: 12, name: "P00012" },
                },
                {
                    product: { id: 57, display_name: "josv" },
                    quantity: 1,
                    move_in: { id: 70 },
                    receipt_date: "04/22/2026",
                    uom_id: { display_name: "Units" },
                    is_late: false,
                    document_in: { _name: "purchase.order", id: 12, name: "P00012" },
                },
                {
                    product: { id: 57, display_name: "josv" },
                    quantity: 5,
                    move_in: { id: 71 },
                    receipt_date: "04/24/2026",
                    uom_id: { display_name: "Units" },
                    is_late: false,
                    document_in: { _name: "purchase.order", id: 13, name: "P00012" },
                },
            ],
        },
        openView: () => {},
        reloadReport: () => {},
    };

    const component = await mountWithCleanup(ForecastedDetails, { props });
    expect(component.mergesLinesData).toEqual({
        0: { rowcount: 2, tot_qty: 2 },
    });
    // The XML applies the class "fw-bold" to the <a> tag of the document.
    const documentLinks = queryAll("tr.collapseGroup_57 td:has(a)");
    expect(documentLinks.length).toBe(2);
    const firstVisibleText = documentLinks[0].parentElement.textContent;
    expect(firstVisibleText).toInclude("P00012");
    expect(firstVisibleText).toInclude("2.00 Units");
    expect(firstVisibleText).toInclude("04/22/2026");
    const secondVisibleText = documentLinks[1].parentElement.textContent;

    expect(secondVisibleText).toInclude("P00012");
    expect(secondVisibleText).toInclude("5.00 Units");
    expect(secondVisibleText).toInclude("04/24/2026");
});
