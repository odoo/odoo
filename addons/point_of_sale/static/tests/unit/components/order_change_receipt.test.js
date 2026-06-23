import { test, expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const normalizeText = (value = "") => value.replace(/\s+/g, " ").trim();

const renderOrderChangeReceipt = (store, order, opts = {}) => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const categoryIds = new Set(store.models["pos.category"].getAll().map((c) => c.id));
    const changes = generator.generatePreparationData(categoryIds, opts);
    const tickets = changes.map((data) =>
        renderToElement("point_of_sale.pos_order_change_receipt", data)
    );
    return { changes, tickets };
};

const renameProduct = (productTemplate, name) => {
    productTemplate.name = name;
    productTemplate.display_name = name;
    productTemplate.product_variant_ids[0].name = name;
    productTemplate.product_variant_ids[0].display_name = name;
};

const expectOrderChangeTicket = (ticket, expected) => {
    if (expected.title) {
        const titleEl = ticket.querySelector("div[name='body'] .text-insane");
        expect(Boolean(titleEl)).toBe(true, {
            message: "Ticket should have a title element",
        });
        expect(normalizeText(titleEl.textContent)).toInclude(expected.title);
    }

    if (expected.is_reprint) {
        const body = normalizeText(ticket.querySelector("div[name='body']").textContent);
        expect(body).toInclude("DUPLICATE");
    } else if (expected.is_reprint === false) {
        const body = normalizeText(ticket.querySelector("div[name='body']").textContent);
        expect(body.includes("DUPLICATE")).toBe(false, {
            message: "Ticket should not contain DUPLICATE text",
        });
    }

    if (expected.config_name) {
        const header = ticket.querySelector("div[name='employee-info']");
        expect(Boolean(header)).toBe(true, {
            message: "Ticket should have employee-info header",
        });
        expect(normalizeText(header.textContent)).toInclude(expected.config_name);
    }

    if (expected.employee_name) {
        const header = ticket.querySelector("div[name='employee-info']");
        expect(normalizeText(header.textContent)).toInclude(expected.employee_name);
    }

    if (expected.order_reference) {
        const text = normalizeText(ticket.textContent);
        expect(text).toInclude(expected.order_reference);
    }

    if (expected.preset_name) {
        const preset = ticket.querySelector(".preset-name");
        expect(Boolean(preset)).toBe(true, {
            message: "Ticket should have preset-name element",
        });
        expect(normalizeText(preset.textContent)).toInclude(expected.preset_name);
    } else if (expected.preset_name === false) {
        expect(Boolean(ticket.querySelector(".preset-name"))).toBe(false, {
            message: "Ticket should not have preset-name element",
        });
    }

    if (expected.orderlines) {
        const lines = [...ticket.querySelectorAll(".orderline")];
        expect(lines).toHaveLength(expected.orderlines.length);
        expected.orderlines.forEach((line, index) => {
            const orderline = lines[index];
            if (line.name) {
                const productName = orderline.querySelector(".product-name");
                expect(normalizeText(productName.textContent)).toInclude(line.name);
            }
            if (line.quantity) {
                expect(normalizeText(orderline.textContent)).toInclude(line.quantity);
            }
            if (line.customer_note) {
                const note = orderline.querySelector(".text-italic");
                expect(Boolean(note)).toBe(true, {
                    message: `Order line ${index} should have a customer note`,
                });
                expect(normalizeText(note.textContent)).toInclude(line.customer_note);
            }
        });
    }

    if (expected.internal_note) {
        const noteContainer = ticket.querySelector(".new-changes");
        expect(Boolean(noteContainer)).toBe(true, {
            message: "Ticket should have internal/customer note section",
        });
        expect(normalizeText(noteContainer.textContent)).toInclude(expected.internal_note);
    }

    if (expected.general_customer_note) {
        const sections = [...ticket.querySelectorAll(".new-changes")];
        const found = sections.some((s) =>
            normalizeText(s.textContent).includes(expected.general_customer_note)
        );
        expect(found).toBe(true, {
            message: `Ticket should contain general customer note: ${expected.general_customer_note}`,
        });
    }
};

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
