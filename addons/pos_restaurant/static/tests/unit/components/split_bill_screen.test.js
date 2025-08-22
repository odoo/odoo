import { describe, test, expect } from "@odoo/hoot";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("split_bill_screen.js", () => {
    test("_getSplitOrderName", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const screen = await mountWithCleanup(SplitBillScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        const originalName = "T1";
        const result = screen._getSplitOrderName(originalName);
        expect(result).toBe("T1B");
    });

    describe("onClickLine", () => {
        test("increments quantity and price tracker on regular line", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);
            const screen = await mountWithCleanup(SplitBillScreen, {
                props: {
                    orderUuid: order.uuid,
                },
            });
            const line = order.getOrderlines()[0];
            screen.onClickLine(line);
            expect(screen.qtyTracker[line.uuid]).toBe(1);
            expect(screen.priceTracker[line.uuid] > 0).toBe(true);
            screen.onClickLine(line);
            expect(screen.qtyTracker[line.uuid]).toBe(2);
        });

        test("handles combo line and its child lines", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            const comboTemplate = store.models["product.template"].get(7);
            const comboItem1 = store.models["product.combo.item"].get(1);
            const comboItem2 = store.models["product.combo.item"].get(3);
            const line = await store.addLineToOrder(
                {
                    product_tmpl_id: comboTemplate,
                    payload: [
                        [
                            {
                                combo_item_id: comboItem1,
                                qty: 1,
                            },
                            {
                                combo_item_id: comboItem2,
                                qty: 1,
                            },
                        ],
                        [],
                    ],
                    configure: true,
                },
                order
            );
            expect(order.lines.length).toBe(3);
            expect(line.product_id.product_tmpl_id).toBe(comboTemplate);
            expect(line.combo_line_ids.length).toBe(2);
            expect(line.combo_line_ids[0].product_id.id).toBe(comboItem1.product_id.id);
            expect(line.combo_line_ids[1].product_id.id).toBe(comboItem2.product_id.id);
            const screen = await mountWithCleanup(SplitBillScreen, {
                props: {
                    orderUuid: order.uuid,
                },
            });
            screen.onClickLine(order.lines[0]);
            expect(screen.qtyTracker[order.lines[0].uuid]).toBe(1);
            expect(screen.qtyTracker[order.lines[1].uuid]).toBe(1);
            expect(screen.qtyTracker[order.lines[2].uuid]).toBe(1);
        });
    });

    test("_getSentQty", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const screen = await mountWithCleanup(SplitBillScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        const ogLine = { qty: 3, preparationKey: "o1" };
        const newLine = { qty: 2, preparationKey: "n1" };
        const sent = screen._getSentQty(ogLine, newLine, 2);
        expect(sent["o1"]).toBe(1);
        expect(sent["n1"]).toBe(1);
    });

    test("_getOrderName", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const screen = await mountWithCleanup(SplitBillScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        expect(screen._getOrderName({ table_id: { table_number: 3 } })).toBe("3");
        expect(screen._getOrderName({ floatingOrderName: "ToGo" })).toBe("ToGo");
        expect(screen._getOrderName({})).toBe("");
    });

    test("setLineQtyStr", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const screen = await mountWithCleanup(SplitBillScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        const line = order.getOrderlines()[0];
        screen.qtyTracker[line.uuid] = 2;
        screen.setLineQtyStr(line);
        expect(line.uiState.splitQty).toBe("2 / 3");
    });

    test("createSplittedOrder", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const table = store.models["restaurant.table"].get(2);
        order.table_id = table;
        const screen = await mountWithCleanup(SplitBillScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        const line = order.getOrderlines()[0];
        screen.qtyTracker[line.uuid] = 2;
        const originalUUID = order.uuid;
        await screen.createSplittedOrder();
        const currentOrder = store.getOrder();
        expect(currentOrder.floating_order_name).toBe("1B");
        expect(currentOrder.uuid).not.toBe(originalUUID);
        expect(currentOrder.getOrderlines().length).toBe(1);
        expect(currentOrder.getOrderlines()[0].getQuantity()).toBe(2);
        expect(order.getOrderlines()[0].getQuantity()).toBe(1);
    });
});
