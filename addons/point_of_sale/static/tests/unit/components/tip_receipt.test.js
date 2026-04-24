import { test } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { expectTipTicket, renderTipReceipt } from "../receipt_utils";

definePosModels();

test("tip ticket renders title, totals, tip and signature lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 2 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        total_amount: "20.00",
        subtotal_amount: "20.00",
        is_tip_line: true,
        is_signature_line: true,
        is_company_info: true,
    });
});

test("tip ticket renders customer name when provided", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(15);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order, "John Doe");

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        name: "John Doe",
        total_amount: "15.00",
    });
});

test("tip ticket does not render name element when name is empty", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(5);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order, "");

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        name: false,
        total_amount: "5.00",
    });
});

test("tip ticket renders logo when configured", async () => {
    const store = await setupPosEnv();
    store.config.logo =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        logo: true,
        title: "Tip Receipt",
        total_amount: "10.00",
    });
});

test("tip ticket does not render logo when not configured", async () => {
    const store = await setupPosEnv();
    store.config.logo = false;
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        logo: false,
        title: "Tip Receipt",
        total_amount: "10.00",
    });
});

test("tip ticket renders correct total for multiple quantities", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 4 }, order);
    line.setUnitPrice(25);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        total_amount: "100.00",
        subtotal_amount: "100.00",
        is_tip_line: true,
        is_signature_line: true,
        is_company_info: true,
    });
});
