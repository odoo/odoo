import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { renderToElement } from "@web/core/utils/render";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const saleDetails = (employee_name) => ({
    employee_name,
    currency: { total_paid: 10 },
    products: [],
    refund_products: [],
    cancelled_products: [],
    payments: [{ name: "Cash", total: 10 }],
    taxes: [],
});

test("prints the session report then one report per employee until a print fails", async () => {
    const store = await setupPosEnv();
    onRpc("report.point_of_sale.report_saledetails", "get_sale_details", () => saleDetails());
    onRpc("pos.session", "get_employees_sale_details", () =>
        ["Alice", "Bob", "Carol"].map(saleDetails)
    );
    const printed = [];
    patchWithCleanup(store.ticketPrinter, {
        async generateIframe(template, data) {
            return renderToElement(template, data);
        },
        async printWithFallback({ iframe }) {
            const name = iframe.textContent.match(/Employee:\s*(\w+)/)?.[1] ?? "Session";
            printed.push(name);
            return { successful: name !== "Bob" };
        },
    });

    await mountWithCleanup(SaleDetailsButton, {});
    await contains(".js_connected").click();
    expect(".modal #include_employee_reports").toBeChecked();
    await contains(".modal .btn-primary").click();

    expect(printed).toEqual(["Session", "Alice", "Bob"]);
});

test("prints only the session report when employee reports are disabled", async () => {
    const store = await setupPosEnv();
    onRpc("pos.session", "get_employees_sale_details", () => {
        throw new Error("Employee reports should not be fetched");
    });
    const printed = [];
    patchWithCleanup(store.ticketPrinter, {
        async printSaleDetailsReceipt() {
            printed.push("Session");
            return { successful: true };
        },
    });

    await mountWithCleanup(SaleDetailsButton, {});
    await contains(".js_connected").click();
    await contains(".modal #include_employee_reports").click();
    await contains(".modal .btn-primary").click();

    expect(printed).toEqual(["Session"]);
});
