import { test, describe, expect } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
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

test("sendDraftOrderToServer updateLastOrderChange", async () => {
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
