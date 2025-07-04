import { test, expect, describe } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { ConnectionLostError } from "@web/core/network/rpc";

definePosModels();

describe("pos_store.js", () => {
    test("getProductPrice", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);
        const price = store.getProductPrice(product);
        expect(price).toBe(3.45);
        order.setPricelist(null);

        const newPrice = store.getProductPrice(product);
        expect(newPrice).toBe(115.0);

        const formattedPrice = store.getProductPrice(product, false, true);
        expect(formattedPrice).toBe("$\u00a0115.00");
    });

    test("setTip", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store); // Should have 2 lines
        expect(order.lines.length).toBe(2);

        await store.setTip(50);
        expect(order.is_tipped).toBe(true);
        expect(order.tip_amount).toBe(50);
        expect(order.lines.length).toBe(3); // 2 original lines + 1 tip line
    });

    describe("syncAllOrders", () => {
        test("simple sync", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("string");
            expect(order.lines[1].id).toBeOfType("string");

            await store.syncAllOrders();
            // Object should be updated in place
            expect(store.getPendingOrder().orderToCreate).toHaveLength(0);
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("number");
            expect(order.lines[1].id).toBeOfType("number");

            const noSync = await store.syncAllOrders();
            expect(noSync).toBe(undefined);
            expect(store.models["pos.order"].length).toBe(2); // One order created during setupPosEnv
        });

        test("sync specific order", async () => {
            const store = await setupPosEnv();
            const order1 = await getFilledOrder(store);
            const order2 = await getFilledOrder(store);

            expect(store.getPendingOrder().orderToCreate).toHaveLength(2);
            expect(order1.lines).toHaveLength(2);
            expect(order1.lines[0].id).toBeOfType("string");
            expect(order1.lines[1].id).toBeOfType("string");

            expect(order2.lines).toHaveLength(2);
            expect(order2.lines[0].id).toBeOfType("string");
            expect(order2.lines[1].id).toBeOfType("string");

            await store.syncAllOrders({ orders: [order1] });
            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(order1.lines).toHaveLength(2);
            expect(order1.lines[0].id).toBeOfType("number");
            expect(order1.lines[1].id).toBeOfType("number");

            expect(order2.lines).toHaveLength(2);
            expect(order2.lines[0].id).toBeOfType("string");
            expect(order2.lines[1].id).toBeOfType("string");

            const data = await store.syncAllOrders();
            expect(data).toHaveLength(1);
            expect(store.getPendingOrder().orderToCreate).toHaveLength(0);
            expect(order2.lines).toHaveLength(2);
            expect(order2.lines[0].id).toBeOfType("number");
            expect(order2.lines[1].id).toBeOfType("number");
        });

        test("sync no network should not raise error", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("string");
            expect(order.lines[1].id).toBeOfType("string");

            store.data.network.offline = true;
            const data = await store.syncAllOrders();
            expect(data).toBeInstanceOf(ConnectionLostError);
            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("string");
            expect(order.lines[1].id).toBeOfType("string");
        });

        test("insync order should not be re-synced", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("string");
            expect(order.lines[1].id).toBeOfType("string");
            store.syncingOrders.add(order.id);

            const data = await store.syncAllOrders();
            expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
            expect(data).toBeEmpty();
            expect(order.lines).toHaveLength(2);
            expect(order.lines[0].id).toBeOfType("string");
            expect(order.lines[1].id).toBeOfType("string");
        });
    });

    test("deleteOrders", async () => {
        const store = await setupPosEnv();
        const order1 = await getFilledOrder(store);
        await store.syncAllOrders();
        await store.deleteOrders([order1]);
        expect(store.models["pos.order"].getBy("uuid", order1.uuid).state).toBe("cancel");
    });

    test("productsToDisplay", async () => {
        const store = await setupPosEnv();
        store.selectedCategory = store.models["pos.category"].get(1);
        let products = store.productsToDisplay;
        expect(products.length).toBe(1);
        expect(products[0].id).toBe(5);
        expect(store.selectedCategory.id).toBe(1);
        store.selectedCategory = store.models["pos.category"].get(1);
        store.searchProductWord = "TEST";
        products = store.productsToDisplay;
        expect(products.length).toBe(2);
        expect(products[0].id).toBe(5);
        expect(products[1].id).toBe(6);
        expect(store.selectedCategory).toBe(undefined);
        store.searchProductWord = "TEST 2";
        products = store.productsToDisplay;
        expect(products.length).toBe(1);
        expect(products[0].id).toBe(6);
    });

    test("productToDisplayByCateg", async () => {
        const store = await setupPosEnv();

        // Case 1: Grouping disabled
        store.config.iface_group_by_categ = false;
        let grouped = store.productToDisplayByCateg;
        expect(grouped.length).toBe(1); //Only one group
        expect(grouped[0][0]).toBe(0);
        expect(grouped[0][1].length).toBe(10); //10 products in same group

        // Case 2: Grouping enabled
        store.config.iface_group_by_categ = true;
        grouped = store.productToDisplayByCateg;
        expect(grouped.length).toBe(5);
        // Confirm grouping structure
        for (const [catId, prods] of grouped) {
            expect(Array.isArray(prods)).toBe(true);
            expect(prods.length).toBeGreaterThan(0);
            for (const prod of prods) {
                const categoryIds = prod.pos_categ_ids.map((c) => c.id);
                expect(categoryIds).toInclude(parseInt(catId));
            }
        }

        // Case 3: Grouping with search filtering
        store.searchProductWord = "TEST";
        grouped = store.productToDisplayByCateg;
        expect(grouped.length).toBe(2);
        expect(grouped[0][1][0].name).toBe("TEST");
        expect(grouped[1][1][0].name).toBe("TEST 2");
    });
});
