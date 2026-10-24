import { test, describe, expect } from "@odoo/hoot";
import { waitUntil } from "@odoo/hoot-dom";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import { session } from "@web/session";

definePosSelfModels();

describe("getOnlinePaymentUrl", () => {
    test("pay route params", async () => {
        patchWithCleanup(session, { base_url: "http://localhost:8069" });
        const store = await setupSelfPosEnv("mobile", "table", "each");
        const order = await getFilledSelfOrder(store);

        const url = new URL(store.getOnlinePaymentUrl(order, false));
        expect(url.pathname).toBe(`/pos/pay/${order.id}`);
        expect(url.searchParams.get("access_token")).toBe(order.access_token);
    });

    describe("exit route params", () => {
        test("no exit route", async () => {
            patchWithCleanup(session, { base_url: "http://localhost:8069" });
            const store = await setupSelfPosEnv("mobile", "table", "each");
            const order = await getFilledSelfOrder(store);
            const getExitRoute = (url) => new URL(url).searchParams.get("exit_route");

            // exitRoute=false (kiosk): no exit route building at all.
            expect(getExitRoute(store.getOnlinePaymentUrl(order, false))).toBe(session.base_url);
        });

        test("service mode dynamic qr", async () => {
            patchWithCleanup(session, { base_url: "http://localhost:8069" });
            const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal");
            const order = await getFilledSelfOrder(store);
            const table = store.models["restaurant.table"].getFirst();
            order.table_id = table;
            const getExitRoute = (url) => new URL(url).searchParams.get("exit_route");

            const dynamicQrExit = new URL(getExitRoute(store.getOnlinePaymentUrl(order)));
            expect(dynamicQrExit.pathname).toBe(
                `/pos-self/${store.config.id}/confirmation/${order.access_token}/order`
            );
            expect(dynamicQrExit.searchParams.get("access_token")).toBe(store.access_token);
            expect(dynamicQrExit.searchParams.get("order_identifier")).toBe(order.access_token);
            expect(dynamicQrExit.searchParams.get("table_identifier")).toBeEmpty();
        });

        test("has current table identifier", async () => {
            patchWithCleanup(session, { base_url: "http://localhost:8069" });
            const store = await setupSelfPosEnv("mobile", "table", "each");
            const order = await getFilledSelfOrder(store);
            const table = store.models["restaurant.table"].getFirst();
            table.identifier = "test-table-identifier";
            store.router.addTableIdentifier(table);
            const getExitRoute = (url) => new URL(url).searchParams.get("exit_route");

            const tableExit = new URL(getExitRoute(store.getOnlinePaymentUrl(order)));
            expect(tableExit.pathname).toBe(
                `/pos-self/${store.config.id}/confirmation/${order.access_token}/order`
            );
            expect(tableExit.searchParams.get("table_identifier")).toBe(table.identifier);
            expect(tableExit.searchParams.get("order_identifier")).toBeEmpty();
        });
    });
});

const getOnlinePaymentNotificationCallback = (store) =>
    store.data.channels.find((channel) => channel.channel === "ONLINE_PAYMENT_STATUS")?.method;

test("self_mobile_online_payment_meal: hasPaymentMethod supports mobile online payment", async () => {
    const store = await setupSelfPosEnv("mobile");

    store.config.self_order_online_payment_method_id = 99;

    expect(store.hasPaymentMethod()).toBe(true);
});

test("self_mobile_online_payment_meal: createNewOrder resets in-progress online payment state", async () => {
    const store = await setupSelfPosEnv();

    store.onlinePaymentStatus = "progress";
    store.createNewOrder();

    expect(store.onlinePaymentStatus).toBe(null);
});

// The notification handler is not awaited by the bus, so the status only lands
// once the round trip it starts has settled.
const notifyOnlinePaymentStatus = async (store, payload) => {
    getOnlinePaymentNotificationCallback(store)(payload);
    await waitUntil(() => store.onlinePaymentStatus !== null, { timeout: 500 }).catch(() => {});
};

test("self_mobile_online_payment_meal: websocket ONLINE_PAYMENT_STATUS confirms the paid order", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");
    const order = await getFilledSelfOrder(store);

    // The order has to stay available while the notification is handled, so the
    // server only reports it paid when the handler asks for it.
    onRpc(`/pos-self-order/get-order/${order.id}`, () => {
        order.state = "paid";
        return { "pos.order": [{ id: order.id, access_token: order.access_token }] };
    });
    patchWithCleanup(store.models, { connectNewData() {} });

    const confirmed = [];
    patchWithCleanup(store, {
        confirmationPage(...args) {
            confirmed.push(args);
        },
    });

    await notifyOnlinePaymentStatus(store, { status: "success", order_id: order.id });

    expect(store.onlinePaymentStatus).toBe("success");
    expect(store.paymentError).toBe(false);
    expect(confirmed).toEqual([["order", "mobile", order.access_token]]);
});

test("self_mobile_online_payment_meal: websocket ONLINE_PAYMENT_STATUS ignores another order and marks failures", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "each");
    const order = await getFilledSelfOrder(store);

    onRpc(`/pos-self-order/get-order/${order.id}`, () => ({
        "pos.order": [{ id: order.id, access_token: order.access_token }],
    }));
    patchWithCleanup(store.models, { connectNewData() {} });

    // A notification about an order this device is not showing changes nothing.
    await notifyOnlinePaymentStatus(store, { status: "success", order_id: order.id + 1000 });
    expect(store.onlinePaymentStatus).toBe(null);

    await notifyOnlinePaymentStatus(store, { status: "fail", order_id: order.id });
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
