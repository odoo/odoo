import { test, describe, expect } from "@odoo/hoot";
import { setupPoSEnvForSelfOrder } from "../utils";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

describe("pos_store.js", () => {
    test("initializes lastPrint for Self-Order when there are changes", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store);
        order.pos_reference = "Self-Order";
        order.use_self_order_online_payment = false;
        order.last_order_preparation_change = { lines: {} };
        store.getOrderChanges = () => ({ nbrOfChanges: 1 });
        store.config = { printerCategories: new Set() };

        order.uiState = { lastPrint: false };
        store.setOrder(order);

        expect(order.uiState.lastPrint !== false).toBe(true);
    });

    test("initializes lastPrint for Kiosk order when there are changes", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store);
        order.pos_reference = "Kiosk";
        order.online_payment_method_id = false;
        order.last_order_preparation_change = { lines: {} };
        store.getOrderChanges = () => ({ nbrOfChanges: 2 });
        store.config = { printerCategories: new Set() };

        order.uiState = { lastPrint: false };
        store.setOrder(order);

        expect(order.uiState.lastPrint !== false).toBe(true);
    });

    test("does not initialize lastPrint for normal POS order", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store);
        order.pos_reference = "POS";
        order.last_order_preparation_change = { lines: {} };
        store.getOrderChanges = () => ({ nbrOfChanges: 1 });
        store.config = { printerCategories: new Set() };

        order.uiState = { lastPrint: false };
        store.setOrder(order);

        expect(order.uiState.lastPrint).toBe(false);
    });
});
