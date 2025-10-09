import { test, describe, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder, addComboProduct } from "../utils";
import { mockDate } from "@odoo/hoot-mock";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

describe("self_order_service", () => {
    test("currentOrder", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const order = store.currentOrder;
        const orders = models["pos.order"].getAll();

        expect(orders).toHaveLength(1);
        expect(order.id).toBe(orders[0].id);

        // no Selected Order
        store.selectedOrderUuid = false;
        expect(store.currentOrder.id).toBe(orders[0].id);
        expect(store.selectedOrderUuid).toBe(orders[0].uuid);

        // no Order
        orders[0].delete();
        expect(models["pos.order"].length).toBe(0);
        expect(store.currentOrder.id).toBe(models["pos.order"].getAll()[0].id);
    });

    describe("initProducts", () => {
        test("hide special products", async () => {
            const store = await setupSelfPosEnv();
            const models = store.models;
            const tipProductTmpl = models["product.template"].get(1);

            expect(store.config._pos_special_products_ids.includes(tipProductTmpl.id)).toBe(true);
            expect(store.productByCategIds["0"]).toBeEmpty(); // No Uncategorised products

            models["product.template"].get(14).pos_categ_ids = [];
            store.initData();
            const UncategorisedProducts = store.productByCategIds["0"];
            expect(UncategorisedProducts.find((p) => p.id === tipProductTmpl.id)).toBeEmpty();

            tipProductTmpl.pos_categ_ids = [1];
            store.initData();
            const catg1Products = store.productByCategIds[1];
            expect(catg1Products.find((p) => p.id === tipProductTmpl.id)).toBeEmpty();
        });

        test("availableCategories and computeAvailableCategories", async () => {
            const store = await setupSelfPosEnv();
            const models = store.models;
            models["product.template"].get(14).pos_categ_ids = [];
            store.initData();

            store.computeAvailableCategories();
            expect(models["pos.category"].length).toBe(5);
            expect(store.availableCategories).toHaveLength(6); // Uncategorised also added
            expect(store.availableCategories.map((c) => c.id)).toEqual([1, 2, 4, 3, 5, 0]);

            // When all products have categories - Uncategorised should be not there
            models["product.template"]
                .filter((p) => !p.pos_categ_ids.length)
                .forEach((prd) => prd.update({ pos_categ_ids: [2] }));
            store.initData();
            store.computeAvailableCategories();
            expect(store.availableCategories).toHaveLength(5);
            expect(store.availableCategories.map((c) => c.id)).toEqual([1, 2, 4, 3, 5]);

            // Time availability
            const unAvailableCatg = models["pos.category"].get(1);
            unAvailableCatg.update({
                hour_after: 10,
                hour_until: 12,
            });
            mockDate("2025-11-29 18:00:00");
            store.computeAvailableCategories();
            expect(store.availableCategories).toHaveLength(4);
            expect(store.isCategoryAvailable(unAvailableCatg)).toBeEmpty();
        });
    });

    test("showComboSelectionPage", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const product = models["product.template"].get(7);
        const combo = models["product.combo"].get(2);
        product.combo_ids = [2];

        const defaultReturnValue = { show: true, selectedCombos: [] };
        expect(store.showComboSelectionPage(product)).toMatchObject(defaultReturnValue);
        // only One choice
        models["product.combo.item"].get(3).delete();
        const showCombo = store.showComboSelectionPage(product);
        expect(showCombo.show).toBe(false);
        expect(showCombo.selectedCombos).toHaveLength(1);
        expect(showCombo.selectedCombos[0].combo_item_id.id).toBe(4);
        // qty_max is more than one
        combo.qty_max = 3;
        expect(store.showComboSelectionPage(product)).toMatchObject(defaultReturnValue);
    });

    test("createNewOrder", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        {
            expect(store.config.available_preset_ids.length > 1).toBe(true);
            const order = store.createNewOrder();
            expect(order.preset_id).toBeEmpty();
        }
        models["pos.preset"].forEach((p) => p.id !== 1 && p.delete());
        {
            // automatically select the preset if only one is available
            expect(store.config.available_preset_ids).toHaveLength(1);
            const order = store.createNewOrder();
            expect(order.preset_id.id).toBe(1);
        }
    });

    test("removeLine", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);

        expect(order.lines).toHaveLength(2);
        store.removeLine(order.lines[0]);
        expect(order.lines).toHaveLength(1);
    });

    test("verifyCart", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        await getFilledSelfOrder(store);
        {
            const result = store.verifyCart();
            expect(result).toBe(true);
            expect(store.currentOrder.lines).toHaveLength(2);
        }
        {
            // with unavailable product
            models["product.product"].get(5).self_order_available = false;
            const result = store.verifyCart();
            expect(result).toBe(false);
            expect(store.currentOrder.lines).toHaveLength(1);
        }
    });

    describe("addToCart", () => {
        test("simple flow", async () => {
            const store = await setupSelfPosEnv();
            const models = store.models;
            const product5 = models["product.template"].get(5);
            const product6 = models["product.template"].get(6);

            store.addToCart(product5, 2, "");
            expect(store.currentOrder.lines).toHaveLength(1);
            expect(store.currentOrder.lines[0].qty).toBe(2);

            // with same Product
            store.addToCart(product5, 7, "");
            expect(store.currentOrder.lines).toHaveLength(1);
            expect(store.currentOrder.lines[0].qty).toBe(9);

            // with diffrent Product
            store.addToCart(product6, 4, "");
            expect(store.currentOrder.lines).toHaveLength(2);
            expect(store.currentOrder.lines[1].qty).toBe(4);
        });
        test("Combo Products", async () => {
            const store = await setupSelfPosEnv();
            await addComboProduct(store);

            expect(store.currentOrder.lines).toHaveLength(3);
            const [parent, child1, child2] = store.currentOrder.lines;

            expect(parent.combo_parent_id).toBeEmpty();
            expect(parent.combo_line_ids).toHaveLength(2);
            expect(parent.combo_line_ids[0].id).toBe(child1.id);
            expect(parent.combo_line_ids[1].id).toBe(child2.id);

            expect(child1.combo_parent_id.id).toBe(parent.id);
            expect(child2.combo_parent_id.id).toBe(parent.id);

            expect(parent.qty).toBe(2);
            expect(child1.qty).toBe(2);
            expect(child2.qty).toBe(2);
        });
    });

    test("sendDraftOrderToServer", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);

        expect(order.id).toBeOfType("string");
        expect(order.lines).toHaveLength(2);
        expect(order.lines[0].id).toBeOfType("string");
        expect(order.lines[1].id).toBeOfType("string");

        const syncOrder = await store.sendDraftOrderToServer();
        expect(order.id).toBeOfType("number");
        expect(order.lines).toHaveLength(2);
        expect(order.lines[0].id).toBeOfType("number");
        expect(order.lines[1].id).toBeOfType("number");

        expect(syncOrder.id).toBe(order.id);
        expect(store.currentOrder.id).toBe(syncOrder.id);
        // no other order should be created
        expect(store.models["pos.order"].length).toBe(1);
    });

    describe("cancelOrder", () => {
        test("Normal cancel order", async () => {
            const store = await setupSelfPosEnv();
            const models = store.models;
            const order = await getFilledSelfOrder(store);

            expect(order.lines).toHaveLength(2);
            expect(models["pos.order"].length).toBe(1);
            expect(models["pos.order.line"].length).toBe(2);

            store.cancelOrder();
            expect(order.lines).toHaveLength(0);
            // Order and lines are deleted
            expect(models["pos.order"].length).toBe(0);
            expect(models["pos.order.line"].length).toBe(0);
            expect(store.selectedOrderUuid).toBeEmpty();
        });
        test("Some line are sent", async () => {
            const store = await setupSelfPosEnv();
            const models = store.models;
            const order = await getFilledSelfOrder(store);
            const line1 = order.lines[0];

            expect(order.lines).toHaveLength(2);
            expect(line1.qty).toBe(3);
            await store.sendDraftOrderToServer();
            order.recomputeChanges();

            const product8 = models["product.template"].get(8);
            store.addToCart(product8, 2, "");
            expect(order.lines).toHaveLength(3);
            expect(models["pos.order.line"].length).toBe(3);

            line1.qty = 6; // 3 qty are sent
            store.cancelOrder();
            // unsent line were deleted
            expect(order.lines).toHaveLength(2);
            expect(line1.qty).toBe(3); // qty reset to 3
            expect(models["pos.order"].length).toBe(1);
            expect(models["pos.order.line"].length).toBe(2);
        });
    });

    test("cancelBackendOrder", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);

        const syncOrder = await store.sendDraftOrderToServer();
        expect(order.id).toBeOfType("number");
        expect(order.lines[0].id).toBeOfType("number");
        expect(order.lines[1].id).toBeOfType("number");
        expect(syncOrder.id).toBe(order.id);

        await store.cancelBackendOrder();

        expect(order.state).toBe("cancel");
        expect(store.router.activeSlot).toBe("default");
    });
});
