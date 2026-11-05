import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { SplitBillScreen } from "@point_of_sale/app/screens/split_bill_screen/split_bill_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("_getSplitOrderName", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const screen = await mountWithCleanup(SplitBillScreen, {
        props: { orderUuid: order.uuid },
    });

    expect(screen._getSplitOrderName("T1")).toBe("T1B");
});

test("Selecting a combo line selects matching quantities from its components", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboTemplate = store.models["product.template"].get(7);
    const comboItem1 = store.models["product.combo.item"].get(1);
    const comboItem2 = store.models["product.combo.item"].get(3);
    await store.addLineToOrder(
        {
            product_tmpl_id: comboTemplate,
            payload: [
                [
                    { combo_item_id: comboItem1, qty: 2 },
                    { combo_item_id: comboItem2, qty: 1 },
                ],
                [],
            ],
            configure: true,
        },
        order
    );
    order.lines[0].setQuantity(2, Boolean(order.lines[0].combo_line_ids?.length));
    const screen = await mountWithCleanup(SplitBillScreen, {
        props: { orderUuid: order.uuid },
    });

    screen.onClickLine(order.lines[0]);

    expect(screen.qtyTracker[order.lines[0].uuid]).toBe(1);
    expect(screen.qtyTracker[order.lines[1].uuid]).toBe(2);
    expect(screen.qtyTracker[order.lines[2].uuid]).toBe(1);
});

test("Retail split screen only shows payment and pays the selected part", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await mountWithCleanup(SplitBillScreen, {
        props: { orderUuid: order.uuid },
    });

    expect(".splitbill-screen .pay-button button:contains('Payment')").toHaveCount(1);
    expect(".splitbill-screen .split-order-button").toHaveCount(0);
    expect(".splitbill-screen .transfer-split-order").toHaveCount(0);

    let payCalled = false;
    store.pay = () => {
        payCalled = true;
    };
    await contains('.splitbill-screen .orderline .product-name:contains("TEST"):first').click();
    await animationFrame();
    await contains(".splitbill-screen .pay-button button:contains('Payment')").click();
    await animationFrame();

    expect(payCalled).toBe(true);
    expect(store.getOpenOrders()).toHaveLength(2);
});
