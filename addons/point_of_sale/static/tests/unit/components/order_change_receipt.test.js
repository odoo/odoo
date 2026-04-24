import { test, expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import {
    normalizeText,
    renameProduct,
    renderOrderChangeReceipt,
    expectOrderChangeTicket,
} from "../receipt_utils";
import * as Utils from "../ui_utils";

definePosModels();

test("order change ticket renders new lines with product name and quantity", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    store.config.module_pos_restaurant = true;
    renameProduct(product, "Desk Pad");
    await store.addLineToOrder({ product_tmpl_id: product, qty: 2 }, order);

    const { tickets } = renderOrderChangeReceipt(store, order);
    expect(tickets.length).toBeGreaterThan(0);

    expectOrderChangeTicket(tickets[0], {
        title: "NEW",
        is_reprint: false,
        config_name: store.config.name,
        orderlines: [{ name: "Desk Pad", quantity: "2" }],
    });
});

test("order change ticket renders cancelled lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    store.config.module_pos_restaurant = true;
    renameProduct(product, "Desk Pad");
    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 3 }, order);

    // Simulate line was already sent to preparation
    order.updateLastOrderChange();

    // Remove line to simulate cancellation
    order.removeOrderline(line);

    const { tickets } = renderOrderChangeReceipt(store, order);
    expect(tickets.length).toBeGreaterThan(0);

    expectOrderChangeTicket(tickets[0], {
        title: "CANCELLED",
        orderlines: [{ name: "Desk Pad", quantity: "3" }],
    });
});

test("order change ticket renders customer note on line", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    store.config.module_pos_restaurant = true;
    renameProduct(product, "Burger");
    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setCustomerNote("No onions please");

    const { tickets } = renderOrderChangeReceipt(store, order);
    expect(tickets.length).toBeGreaterThan(0);

    expectOrderChangeTicket(tickets[0], {
        title: "NEW",
        orderlines: [{ name: "Burger", quantity: "1", customer_note: "No onions please" }],
    });
});

test("order change ticket renders general customer note section", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    store.config.module_pos_restaurant = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const categoryIds = new Set(store.models["pos.category"].getAll().map((c) => c.id));
    const changes = generator.generatePreparationData(categoryIds);
    expect(changes.length).toBeGreaterThan(0);
    changes[changes.length - 1].extra_data.general_customer_note = "Allergic to nuts";

    const ticket = renderToElement(
        "point_of_sale.pos_order_change_receipt",
        changes[changes.length - 1]
    );

    const noteSection = [...ticket.querySelectorAll(".new-changes")].find((el) =>
        normalizeText(el.textContent).includes("CUSTOMER NOTE")
    );
    expect(Boolean(noteSection)).toBe(true, {
        message: "Ticket should have CUSTOMER NOTE section",
    });
    expect(normalizeText(noteSection.textContent)).toInclude("Allergic to nuts");
});

test("order change ticket renders multiple new lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);
    const product2 = store.models["product.template"].get(6);

    store.config.module_pos_restaurant = true;
    renameProduct(product1, "Burger");
    renameProduct(product2, "Pizza");
    await store.addLineToOrder({ product_tmpl_id: product1, qty: 2 }, order);
    await store.addLineToOrder({ product_tmpl_id: product2, qty: 1 }, order);

    const { tickets } = renderOrderChangeReceipt(store, order);
    expect(tickets.length).toBeGreaterThan(0);

    expectOrderChangeTicket(tickets[0], {
        title: "NEW",
        orderlines: [
            { name: "Burger", quantity: "2" },
            { name: "Pizza", quantity: "1" },
        ],
    });
});
