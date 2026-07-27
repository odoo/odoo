import { test, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv, setupAndMountPosApp, createComboSetup } from "../utils";
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

test("test_printer_restricts_to_allowed_categories_for_combo: only combo items in allowed categories print", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, module_pos_restaurant: true });

    const { template: comboTmpl } = createComboSetup(store, {
        id: 8500,
        name: "Office Combo",
        price: 40,
        categoryId: 1,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 3", price: 16 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 5", price: 25 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 8", price: 40 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    comboTmpl.pos_categ_ids = [store.models["pos.category"].get(1)];

    const comboProduct5 = store.models["product.template"]
        .getAll()
        .find((p) => p.name === "Combo Product 5");
    if (comboProduct5) {
        comboProduct5.pos_categ_ids = [store.models["pos.category"].get(2)];
    }
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    const order = store.getOrder();
    const { tickets } = renderOrderChangeReceipt(store, order, {}, [2]);
    expectOrderChangeTicket(tickets[0], {
        orderlines: [
            { name: "Office Combo", quantity: "1" },
            { name: "Combo Product 5", quantity: "1" },
        ],
        invisibleInDom: ["Combo Product 3", "Combo Product 8"],
    });
});

test("test_printer_not_linked_to_any_combo_category: printer only shows non-combo items in its category", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, module_pos_restaurant: true });

    createComboSetup(store, {
        id: 8600,
        name: "Office Combo",
        price: 40,
        categoryId: 1,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 5", price: 25 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });

    const category2 = store.models["pos.category"].get(2);
    store.models["product.template"].get(5).pos_categ_ids = [category2];
    store.models["product.product"].get(5).pos_categ_ids = [category2];
    await animationFrame();
    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.clickDisplayedProduct("TEST");
    const order = store.getOrder();
    const { tickets } = renderOrderChangeReceipt(store, order, {}, [2]);
    expectOrderChangeTicket(tickets[0], {
        orderlines: [{ name: "TEST", quantity: "1" }],
        invisibleInDom: ["Office Combo", "Combo Product 5"],
    });
});
