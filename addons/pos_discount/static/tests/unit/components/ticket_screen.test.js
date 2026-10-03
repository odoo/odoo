import { test, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_onUpdateSelectedOrderline: refund skips discount line", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const discountProduct = store.models["product.template"].get(151);

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: discountProduct,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);

    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({
        key: "Enter",
        buffer: "3",
    });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});

test("_onUpdateSelectedOrderline: a percent discount is recomputed on the refund, never split", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const productLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 5 },
        order
    );
    await store.applyDiscount(10, "percent", order);
    await animationFrame(); // flush the debounced re-apply the new lines trigger
    const discountLine = order.discountLines[0];
    expect(discountLine.priceIncl).toBe(-57.5);
    expect(order.priceIncl).toBe(517.5);

    order.state = "paid";
    order.setOrderPrices();

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(productLine.id);

    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });

    expect(order.uiState.lineToRefund[discountLine.uuid]?.qty ?? 0).toBe(0);

    await ticketScreen.onDoRefund();
    await animationFrame(); // onDoRefund does not await applyDiscount

    const refundOrder = store.getOrder();
    expect(refundOrder.discountLines.length).toBe(1);
    expect(refundOrder.discountLines[0].tax_ids.map((tax) => tax.id)).toEqual([1]);
    expect(refundOrder.discountLines[0].priceIncl).toBe(-11.5);
    expect(refundOrder.priceIncl).toBe(-103.5); // 517.50 / 5
    expect(discountLine.refundedQty).toBe(0);
});

test("_onUpdateSelectedOrderline: a fixed discount is refunded pro rata, per tax group", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const line15 = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 4 },
        order
    );
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(6), qty: 2 },
        order
    );
    await store.applyDiscount(71, "fixed", order);
    await animationFrame();

    const discount15 = order.discountLines.find((line) => line.tax_ids[0].id === 1);
    const discount25 = order.discountLines.find((line) => line.tax_ids[0].id === 2);
    expect(discount15.priceIncl).toBe(-46);
    expect(discount25.priceIncl).toBe(-25);
    expect(order.priceIncl).toBe(639);

    order.state = "paid";
    order.setOrderPrices();

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line15.id);

    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(order.uiState.lineToRefund[discount15.uuid].qty).toBe(0.25);
    expect(order.uiState.lineToRefund[discount25.uuid]?.qty ?? 0).toBe(0);

    await ticketScreen.onDoRefund();

    const refundOrder = store.getOrder();
    expect(refundOrder.discountLines.length).toBe(1);
    expect(refundOrder.discountLines[0].tax_ids.map((tax) => tax.id)).toEqual([1]);
    expect(refundOrder.discountLines[0].priceIncl).toBe(-11.5); // a quarter of 46.00
    expect(refundOrder.priceIncl).toBe(-103.5);
});
