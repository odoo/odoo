import { expect, test } from "@odoo/hoot";
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";

test("forecast detail sameDocument receipt date", async () => {
    const document_in = { id: 10, _name: "stock.picking", name: "PICK/001" };
    const line1 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const line2 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const doc1 = { lines: [line1, line2] };
    const forecast1 = new ForecastedDetails({ docs: doc1 });
    forecast1.OnHandLinesPerProduct = {};
    forecast1.NotAvailableLinesPerProduct = {};
    forecast1._mergeLines();
    expect(forecast1.mergesLinesData[0]["rowcount"]).toBe(2);

    const line3 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const line4 = { receipt_date: "2024-01-03", product: { id: 1 }, document_in };
    const doc2 = { lines: [line3, line4] };
    const forecast2 = new ForecastedDetails({ docs: doc2 });
    forecast2.OnHandLinesPerProduct = {};
    forecast2.NotAvailableLinesPerProduct = {};
    forecast2._mergeLines();
    expect(forecast2.mergesLinesData).toEqual({});
});
