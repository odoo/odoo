import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

definePosSelfModels();

const getOnlinePaymentNotificationCallback = (store) =>
    store.data.channels.find((channel) => channel.channel === "ONLINE_PAYMENT_STATUS")?.method;

test("self_mobile_online_payment_meal: hasPaymentMethod supports mobile online payment", async () => {
    const store = await setupSelfPosEnv("mobile");

    store.config.self_order_online_payment_method_id = 99;

    expect(store.hasPaymentMethod()).toBe(true);
});

test("self_mobile_online_payment_meal_table: getOnlinePaymentUrl builds mobile return route with table", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");
    const currentOrder = await getFilledSelfOrder(store);

    store.access_token = "self-order-token";
    patchWithCleanup(store, {
        get currentTable() {
            return { identifier: "table-1" };
        },
    });

    const paymentUrl = store.getOnlinePaymentUrl(
        {
            id: 42,
            access_token: "order-token",
            config_id: { id: store.config.id },
        },
        true
    );

    const encodedExitRoute = new URL(paymentUrl).searchParams.get("exit_route");
    const exitRoute = decodeURIComponent(encodedExitRoute);

    expect(paymentUrl.includes(`${session.base_url}/pos/pay/42?access_token=order-token`)).toBe(
        true
    );
    expect(
        exitRoute.includes(
            `/pos-self/${store.config.id}/confirmation/${currentOrder.access_token}/order`
        )
    ).toBe(true);
    expect(exitRoute.includes("access_token=self-order-token")).toBe(true);
    expect(exitRoute.includes("table_identifier=table-1")).toBe(true);
});

test("test_online_payment_kiosk_qr_code: getOnlinePaymentUrl can skip exit route", async () => {
    const store = await setupSelfPosEnv("kiosk");

    const paymentUrl = store.getOnlinePaymentUrl(
        {
            id: 55,
            access_token: "order-token",
            config_id: { id: store.config.id },
        },
        false
    );

    expect(paymentUrl).toBe(
        `${session.base_url}/pos/pay/55?access_token=order-token&exit_route=${encodeURIComponent(
            session.base_url
        )}`
    );
});

test("self_mobile_online_payment_meal: createNewOrder resets in-progress online payment state", async () => {
    const store = await setupSelfPosEnv();

    store.onlinePaymentStatus = "progress";
    store.createNewOrder();

    expect(store.onlinePaymentStatus).toBe(null);
});

test("self_mobile_online_payment_meal: websocket ONLINE_PAYMENT_STATUS updates status and triggers confirmation", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");
    const order = await getFilledSelfOrder(store);

    const callback = getOnlinePaymentNotificationCallback(store);
    expect(callback).not.toBe(false);

    order.access_token = null;
    const linkedOrder = store.models["pos.order"].create({ access_token: "server-token" });

    callback({
        status: "success",
        data: {
            "pos.order": [{ uuid: order.uuid, access_token: linkedOrder.access_token }],
        },
    });

    expect(store.onlinePaymentStatus).toBe("success");
    expect(store.paymentError).toBe(false);
});

test("self_mobile_online_payment_meal: websocket ONLINE_PAYMENT_STATUS ignores unmatched order and marks failures", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");
    const order = await getFilledSelfOrder(store);

    const callback = getOnlinePaymentNotificationCallback(store);
    expect(callback).not.toBe(false);

    callback({
        status: "success",
        data: {
            "pos.order": [{ uuid: "another-order-uuid", access_token: "other-token" }],
        },
    });
    expect(store.onlinePaymentStatus).toBe(null);

    callback({
        status: "fail",
        data: {
            "pos.order": [{ uuid: order.uuid, access_token: order.access_token }],
        },
    });
    expect(store.onlinePaymentStatus).toBe("fail");
    expect(store.paymentError).toBe(true);
});

test("test_online_payment_mobile_self_order_preparation_changes: sendDraftOrderToServer updateLastOrderChange", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    store.config.self_ordering_mode = "mobile";
    const product4 = store.models["product.template"].get(11);
    await store.addToCart(product4, 1, "");
    await store.sendDraftOrderToServer();
    expect(Object.keys(order.prep_order_ids)).toHaveLength(0);

    store.config.self_ordering_pay_after = "meal";
    const product3 = store.models["product.template"].get(10);
    await store.addToCart(product3, 1, "");
    await store.sendDraftOrderToServer();
    expect(Object.keys(order.prep_order_ids[0].prep_line_ids)).toHaveLength(4);
});

test("test_online_payment_mobile_self_order_preparation_changes: shouldUpdateLastOrderChange", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");

    store.config.self_order_online_payment_method_id = 99;
    expect(store.shouldUpdateLastOrderChange()).toBe(false);

    store.config.self_ordering_pay_after = "meal";
    expect(store.shouldUpdateLastOrderChange()).toBe(true);
});

test("test_kiosk_cart_restore_and_cancel", async () => {
    const store = await setupSelfPosEnv("kiosk");
    const order = await getFilledSelfOrder(store);

    expect(order.lines).toHaveLength(2);
    store.cancelOrder();

    expect(order.lines).toHaveLength(0);
    expect(store.selectedOrderUuid).toBeEmpty();

    await store.addToCart(store.models["product.template"].get(5), 1, "");
    expect(store.currentOrder.lines).toHaveLength(1);
});
