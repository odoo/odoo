import { test, expect, describe } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { ConnectionLostError } from "@web/core/network/rpc";
import { onRpc } from "@web/../tests/web_test_helpers";
import { imageUrl } from "@web/core/utils/urls";
import { prepareRoundingVals } from "../accounting/utils";

definePosModels();

describe("pos_store.js", () => {
    test("setTip", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store); // Should have 2 lines
        expect(order.lines.length).toBe(2);

        await store.setTip(50);
        expect(order.is_tipped).toBe(true);
        expect(order.tip_amount).toBe(50);
        expect(order.lines.length).toBe(3); // 2 original lines + 1 tip line
    });

    test("orderNoteFormat", async () => {
        const store = await setupPosEnv();
        const str = store.getStrNotes("string");
        expect(str).toBeOfType("string");
        expect(str).toBe("string");
        const json2str = store.getStrNotes([{ text: "json", colorIndex: 0 }]);
        expect(json2str).toBeOfType("string");
        expect(json2str).toBe("json");
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
            expect(store.models["pos.order"].length).toBe(1);
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
            store.syncingOrders.add(order.uuid);

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

    test("changesToOrderNoPrepCateg", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const orderChange = store.changesToOrder(order, new Set([]), false);
        expect(orderChange.new.length).toBe(0);
        expect(orderChange.cancelled.length).toBe(0);
    });

    test("orderContainsProduct", async () => {
        const store = await setupPosEnv();
        await getFilledOrder(store);
        const product1 = store.models["product.template"].get(5);
        const product2 = store.models["product.template"].get(6);
        const product3 = store.models["product.template"].get(8);
        expect(store.orderContainsProduct(product1)).toBe(true);
        expect(store.orderContainsProduct(product2)).toBe(true);
        expect(store.orderContainsProduct(product3)).toBe(false);
        const order = await store.addNewOrder();
        await store.addLineToOrder(
            {
                product_tmpl_id: product3,
                qty: 1,
            },
            order
        );

        expect(store.orderContainsProduct(product1)).toBe(true);
        expect(store.orderContainsProduct(product2)).toBe(true);
        expect(store.orderContainsProduct(product3)).toBe(true);
    });

    test("generateReceiptsDataToPrint", async () => {
        const store = await setupPosEnv();
        const pos_categories = store.models["pos.category"].getAll().map((c) => c.id);
        const order = await getFilledOrder(store);
        order.lines[1].setNote('[{"text":"Wait","colorIndex":0}]');

        order.lines[0].setCustomerNote("Test Orderline Customer Note");
        const orderChange = store.changesToOrder(order, new Set([...pos_categories]), false);

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
            combo_parent_uuid: undefined,
            customer_note: "Test Orderline Customer Note",
            product_id: 5,
            attribute_value_names: [],
            quantity: 3,
            note: "",
            pos_categ_id: 1,
            pos_categ_sequence: 1,
            display_name: "TEST",
            group: undefined,
            isCombo: false,
        });
        expect(receiptsData[0].changes.data[1]).toEqual({
            uuid: order.lines[1].uuid,
            name: "TEST 2",
            basic_name: "TEST 2",
            combo_parent_uuid: undefined,
            customer_note: "",
            product_id: 6,
            attribute_value_names: [],
            quantity: 2,
            note: "Wait",
            pos_categ_id: 2,
            pos_categ_sequence: 2,
            display_name: "TEST 2",
            group: undefined,
            isCombo: false,
        });
    });

    test("filterChangeByCategories", async () => {
        const store = await setupPosEnv();
        const allowedCategories = [1];

        const productA = store.models["product.product"].get(5);
        const productB = store.models["product.product"].get(6);
        productA.parentPosCategIds = [1];
        productB.parentPosCategIds = [2];

        const currentOrderChange = {
            new: [
                { uuid: "combo-parent-uuid", isCombo: true },
                {
                    uuid: "combo-child-a-uuid",
                    combo_parent_uuid: "combo-parent-uuid",
                    product_id: productA.id,
                    isCombo: false,
                },
                {
                    uuid: "combo-child-b-uuid",
                    combo_parent_uuid: "combo-parent-uuid",
                    product_id: productB.id,
                    isCombo: false,
                },
                { uuid: "line1", product_id: productA.id, isCombo: false },
                { uuid: "line2", product_id: productB.id, isCombo: false },
            ],
            cancelled: [],
            noteUpdate: [],
        };

        const filtered = store.filterChangeByCategories(allowedCategories, currentOrderChange);

        const expectedUuids = ["combo-parent-uuid", "combo-child-a-uuid", "line1"];
        const actualUuids = filtered.new.map((c) => c.uuid);

        expect(actualUuids.sort()).toEqual(expectedUuids.sort());
    });

    test("deleteOrders", async () => {
        const store = await setupPosEnv();
        const order1 = await getFilledOrder(store);
        await store.syncAllOrders();
        await store.deleteOrders([order1]);
        expect(store.models["pos.order"].getBy("uuid", order1.uuid)).toBeEmpty();
    });

    test("deleteOrders multiple orders", async () => {
        const store = await setupPosEnv();
        await getFilledOrder(store);
        store.addNewOrder();
        let openOrders = store.getOpenOrders();
        expect(openOrders.length).toBe(2);
        const deletedOrders = await store.deleteOrders(openOrders);
        expect(deletedOrders).toBe(true);
        openOrders = store.getOpenOrders();
        expect(openOrders.length).toBe(0);
    });

    test("getOrderData", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const orderData = store.getOrderData(order);
        expect(orderData).toEqual({
            reprint: undefined,
            pos_reference: "1001",
            config_name: "Hoot",
            time: "10:30",
            tracking_number: "1001",
            preset_time: false,
            preset_name: "In",
            employee_name: "Administrator",
            internal_note: "",
            general_customer_note: "",
            changes: {
                title: "",
                data: [],
            },
        });
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
        expect(products.length).toBe(4);
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
        expect(grouped[0][1].length).toBe(12); //10 products in same group

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

    test("onDeleteOrder", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const deletedOrder = await store.onDeleteOrder(order);
        expect(order.uiState.displayed).toBe(false);
        expect(deletedOrder).toBe(true);
    });

    test("setNextOrderRefs", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await store.setNextOrderRefs(order);
        expect(order.pos_reference).toBeOfType("string");
        expect(order.pos_reference.length).toBeGreaterThan(1);
        expect(order.sequence_number).toBeOfType("integer");
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

    test("getPaymentMethodFmtAmount", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);

        // Case 1: No rounding enabled
        expect(store.getPaymentMethodFmtAmount(cashPm, order)).toBeEmpty();

        // Case 2: Rounding enabled, not limited to cash
        const { cashPm: cash1, cardPm: card1 } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
        expect(store.getPaymentMethodFmtAmount(cash1, order)).toBe("$ 17.85");
        expect(store.getPaymentMethodFmtAmount(card1, order)).toBe("$ 17.85");

        // Case 3: Rounding enabled, only for cash
        const { cashPm: cash2, cardPm: card2 } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
        expect(store.getPaymentMethodFmtAmount(cash2, order)).toBe("$ 17.85");
        expect(store.getPaymentMethodFmtAmount(card2, order)).toBeEmpty();
    });

    describe("cacheReceiptLogo", () => {
        function getCompanyLogo256Url(companyId) {
            const fullUrl = imageUrl("res.company", companyId, "logo", {
                width: 256,
                height: 256,
            });
            const index = fullUrl.indexOf("/web");
            return fullUrl.substring(index);
        }

        test("correctly cached", async () => {
            onRpc(getCompanyLogo256Url("<int:id>"), async (request, { id }) => {
                expect.step(`Company logo ${id} fetched`);
                return `Company logo ${id}`;
            });
            const store = await setupPosEnv();
            const companyId = store.company.id;
            expect.verifySteps([`Company logo ${companyId} fetched`]);
            const { receiptLogoUrl } = store.config;
            expect(receiptLogoUrl).toInclude("data:");
            expect(atob(receiptLogoUrl.split(",")[1])).toInclude(`Company logo ${companyId}`);
        });

        test("fetch failed", async () => {
            onRpc(getCompanyLogo256Url("<int:id>"), async (request, { id }) => {
                expect.step(`Company logo ${id} fetched`);
                throw new Error("Fetch failed");
            });
            const store = await setupPosEnv();
            const companyId = store.company.id;
            expect.verifySteps([`Company logo ${companyId} fetched`]);
            expect(store.config.receiptLogoUrl).toInclude(getCompanyLogo256Url(companyId));
        });

        test("preSyncAllOrders", async () => {
            // This test check prices sign on preSyncAllOrders for refunds
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);

            await store.preSyncAllOrders([order]);
            expect(order.amount_total).toEqual(17.85);
            expect(order.amount_tax).toEqual(2.85);
            expect(order.lines[0].qty).toEqual(3);
            expect(order.lines[0].price_unit).toEqual(3);
            expect(order.lines[0].price_subtotal).toEqual(3);
            expect(order.lines[0].price_subtotal_incl).toEqual(10.35);
            expect(order.lines[1].qty).toEqual(2);
            expect(order.lines[1].price_unit).toEqual(3);
            expect(order.lines[1].price_subtotal).toEqual(3);
            expect(order.lines[1].price_subtotal_incl).toEqual(7.5);

            order.is_refund = true;
            order.lines.forEach((line) => (line.qty = -line.qty));
            await store.preSyncAllOrders([order]);

            expect(order.amount_total).toEqual(-17.85);
            expect(order.amount_tax).toEqual(-2.85);
            expect(order.lines[0].qty).toEqual(-3);
            expect(order.lines[0].price_unit).toEqual(3);
            expect(order.lines[0].price_subtotal).toEqual(3);
            expect(order.lines[0].price_subtotal_incl).toEqual(10.35);
            expect(order.lines[1].qty).toEqual(-2);
            expect(order.lines[1].price_unit).toEqual(3);
            expect(order.lines[1].price_subtotal).toEqual(3);
            expect(order.lines[1].price_subtotal_incl).toEqual(7.5);
        });
    });
});
