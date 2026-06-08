import { before, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

before(() => {
    // Remove mail services and components
    const services = registry.category("services");
    for (const [name] of services.getEntries()) {
        if (
            name.startsWith("mail.") ||
            name.startsWith("discuss.") ||
            ["bus.connection_alert", "bus.monitoring_service"].includes(name)
        ) {
            services.remove(name);
        }
    }
    services.remove("im_status");

    const main_components = registry.category("main_components");
    for (const [name] of main_components.getEntries()) {
        if (name.startsWith("mail.") || name.startsWith("discuss.") || name.startsWith("bus.")) {
            main_components.remove(name);
        }
    }
});

test("forecast detail sameDocument receipt date", async () => {
    patchWithCleanup(ForecastedDetails, {
        // FIXME: even if cumbersome, testing should be done
        // by actually mounting the real thing with some actual data
        // Or lift the business code to a class
        template: xml`<div />`,
    });

    const document_in = { id: 10, _name: "stock.picking", name: "PICK/001" };
    const line1 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const line2 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const doc1 = { lines: [line1, line2], product: [1] };

    const forecast1 = await mountWithCleanup(ForecastedDetails, { props: { docs: doc1 }})
    forecast1.OnHandLinesPerProduct = {};
    forecast1.NotAvailableLinesPerProduct = {};
    forecast1._mergeLines();
    expect(forecast1.mergesLinesData[0]["rowcount"]).toBe(2);

    const line3 = { receipt_date: "2024-01-01", product: { id: 1 }, document_in };
    const line4 = { receipt_date: "2024-01-03", product: { id: 1 }, document_in };
    const doc2 = { lines: [line3, line4], product: [1] };

    const forecast2 = await mountWithCleanup(ForecastedDetails, { props: { docs: doc2 }})
    forecast2.OnHandLinesPerProduct = {};
    forecast2.NotAvailableLinesPerProduct = {};
    forecast2._mergeLines();
    expect(forecast2.mergesLinesData).toEqual({});
});
