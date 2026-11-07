import { test, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { SplitBillScreen } from "@point_of_sale/app/screens/split_bill_screen/split_bill_screen";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

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

test("createSplittedOrder", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const table = store.models["restaurant.table"].get(2);
    order.table_id = table;
    await mountWithCleanup(SplitBillScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });
    // Click the first orderline twice via DOM
    await contains('.splitbill-screen .orderline .product-name:contains("TEST"):first').click();
    await animationFrame();
    await contains('.splitbill-screen .orderline .product-name:contains("TEST"):first').click();
    await animationFrame();
    // Click Split button
    await contains('.splitbill-screen .pay-button button:contains("Split")').click();
    await animationFrame();
    const originalUUID = order.uuid;
    const currentOrder = store.getOrder();
    expect(currentOrder.floating_order_name).toBe("1B");
    expect(currentOrder.uuid).not.toBe(originalUUID);
    expect(currentOrder.getOrderlines().length).toBe(1);
    expect(currentOrder.getOrderlines()[0].getQuantity()).toBe(2);
    expect(order.getOrderlines()[0].getQuantity()).toBe(1);
});

test("transferSplittedOrder splits partial selection then starts transfer", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await mountWithCleanup(SplitBillScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });
    // Click the first orderline once via DOM
    await contains('.splitbill-screen .orderline .product-name:contains("TEST"):first').click();
    await animationFrame();

    let transferCalled = false;
    store.startTransferOrder = () => {
        transferCalled = true;
    };

    // Click Transfer button
    await contains('.splitbill-screen .pay-button button:contains("Transfer")').click();
    await animationFrame();

    expect(transferCalled).toBe(true);
    expect(store.getOpenOrders().length).toBe(2);
});
