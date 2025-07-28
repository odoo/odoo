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

    test("addLineToCurrentOrder", async () => {
        const store = await setupPosEnv();
        store.setOrder(null);
        expect(store.getOrder()).toBe(undefined);
        // Should create order if none exist
        const product = store.models["product.product"].get(5);
        await store.addLineToCurrentOrder({ product_tmpl_id: product.product_tmpl_id });
        expect(store.getOrder()).not.toBe(undefined);
        expect(store.getOrder().lines.length).toBe(1);
        expect(store.getOrder().lines[0].product_id.id).toBe(product.id);
        expect(store.getOrder().lines[0].qty).toBe(1);
        await store.addLineToCurrentOrder({ product_tmpl_id: product.product_tmpl_id, qty: 3 }, {});
        expect(store.getOrder().lines[0].qty).toBe(4);
    });

    test("generateReceiptsDataToPrint", async () => {
        const store = await setupPosEnv();
        const pos_categories = store.models["pos.category"].getAll().map((c) => c.id);
        const order = await getFilledOrder(store);
        order.lines[1].setNote('[{"text":"Wait","colorIndex":0}]');
        const orderChange = store.changesToOrder(order, store.config.preparationCategories, false);

        const { orderData, changes } = store.generateOrderChange(
            order,
            orderChange,
            pos_categories,
            false
        );

        const receiptsData = await store.generateReceiptsDataToPrint(
            orderData,
            changes,
            orderChange
        );
        expect(receiptsData.length).toBe(1);
        expect(receiptsData[0].changes.title).toBe("NEW");
        expect(receiptsData[0].changes.data.length).toBe(2);
        expect(receiptsData[0].changes.data[0]).toEqual({
            uuid: order.lines[0].uuid,
            name: "TEST",
            basic_name: "TEST",
            product_id: 5,
            attribute_value_names: [],
            quantity: 3,
            note: "",
            pos_categ_id: 1,
            pos_categ_sequence: 0,
            display_name: "TEST",
            group: undefined,
            isCombo: undefined,
        });
        expect(receiptsData[0].changes.data[1]).toEqual({
            uuid: order.lines[1].uuid,
            name: "TEST 2",
            basic_name: "TEST 2",
            product_id: 6,
            attribute_value_names: [],
            quantity: 2,
            note: "Wait",
            pos_categ_id: 2,
            pos_categ_sequence: 0,
            display_name: "TEST 2",
            group: undefined,
            isCombo: undefined,
        });
    });

    test("deleteOrders", async () => {
        const store = await setupPosEnv();
        const order1 = await getFilledOrder(store);
        await store.syncAllOrders();
        await store.deleteOrders([order1]);
        expect(store.models["pos.order"].getBy("uuid", order1.uuid).state).toBe("cancel");
    });

    test("deleteOrders multiple orders", async () => {
        const store = await setupPosEnv();
        await getFilledOrder(store);
        store.addNewOrder();
        let openOrders = store.getOpenOrders();
        expect(openOrders.length).toBe(3);
        const deletedOrders = await store.deleteOrders(openOrders);
        expect(deletedOrders).toBe(true);
        openOrders = store.getOpenOrders();
        expect(openOrders.length).toBe(0);
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

    test("firstScreen", async () => {
        const store = await setupPosEnv();
        expect(store.firstScreen).toBe("ProductScreen");
    });

    test("onDeleteOrder", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const deletedOrder = await store.onDeleteOrder(order);
        expect(order.uiState.displayed).toBe(false);
        expect(deletedOrder).toBe(true);
    });

    test("getNextOrderRefs", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await store.getNextOrderRefs(order);
        expect(order.pos_reference).toBeOfType("string");
        expect(order.pos_reference.length).toBeGreaterThan(1);
        expect(order.sequence_number).toBeOfType("integer");
        expect(order.sequence_number).toBeGreaterThan(0);
        expect(order.tracking_number).toBeOfType("string");
        expect(order.tracking_number.length).toBeGreaterThan(2);
    });

    test("pending orders", async () => {
        const store = await setupPosEnv();
        let { orderToCreate, orderToUpdate, orderToDelete } = store.getPendingOrder();
        expect(orderToCreate).toHaveLength(0);
        expect(orderToUpdate).toHaveLength(0);
        expect(orderToDelete).toHaveLength(0);
        const order = await getFilledOrder(store);
        ({ orderToCreate, orderToUpdate, orderToDelete } = store.getPendingOrder());
        expect(order.id).toBe(orderToCreate[0].id);
        // After sync, order should be in 'orderToUpdate'
        await store.syncAllOrders({ orders: [order] });
        store.addPendingOrder([order.id]);
        ({ orderToCreate, orderToUpdate, orderToDelete } = store.getPendingOrder());
        expect(orderToCreate).toHaveLength(0);
        expect(orderToUpdate).toHaveLength(1);
        // Remove pending order
        store.addPendingOrder([order.id], true);
        ({ orderToCreate, orderToUpdate, orderToDelete } = store.getPendingOrder());
        expect(orderToUpdate).toHaveLength(0);
        expect(orderToDelete).toHaveLength(1);
        // Clear pending orders
        store.clearPendingOrder();
        ({ orderToCreate, orderToUpdate, orderToDelete } = store.getPendingOrder());
        expect(orderToDelete).toHaveLength(0);
    });

    test("showScreen", async () => {
        const store = await setupPosEnv();
        let screen = store.mainScreen.component.name;
        expect(screen).toBe("LoginScreen");
        store.showScreen("ProductScreen");
        screen = store.mainScreen.component.name;
        expect(screen).toBe("ProductScreen");
        expect(store.previousScreen).toBe("LoginScreen");
    });
});
