import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { setupPosEnv, makeOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
const { DateTime } = luxon;

definePosModels();

test("_onUpdateSelectedOrderline: refund moves to next", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const comboLine = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(7),
        payload: [
            [
                { combo_item_id: store.models["product.combo.item"].get(1), qty: 1 },
                { combo_item_id: store.models["product.combo.item"].get(3), qty: 1 },
            ],
            [],
        ],
        configure: false,
    });
    const line2Refund = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    // refund `line2Refund`
    const refundedOrder = store.createNewOrder();
    const refundingLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(8), qty: -2 },
        refundedOrder
    );
    line2Refund.refund_orderline_ids = [refundingLine.id];
    refundedOrder.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(comboLine.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "2" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "3" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});

describe("getFilteredOrderList", () => {
    test("filter", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, {
            pos_reference: "O-01",
            state: "draft",
            getScreenData: () => ({ name: "ProductScreen" }),
        });
        makeOrder(store, {
            pos_reference: "O-02",
            state: "draft",
            getScreenData: () => ({ name: "PaymentScreen" }),
        });
        makeOrder(store, { pos_reference: "O-03", state: "cancel" });
        makeOrder(store, { pos_reference: "O-04", state: "paid" });

        screen.state.filter = "SYNCED";
        const syncResult = screen.getFilteredOrderList();
        expect(syncResult.length).toBe(1);
        expect(syncResult[0].pos_reference).toBe("O-04");

        screen.state.filter = "CANCELLED";
        const cancelledResult = screen.getFilteredOrderList();
        expect(cancelledResult.length).toBe(1);
        expect(cancelledResult[0].pos_reference).toBe("O-03");

        screen.state.filter = "ACTIVE_ORDERS";
        const activeResult = screen.getFilteredOrderList();
        expect(activeResult.length).toBe(2);
        expect(activeResult[0].pos_reference).toBe("O-01");
        expect(activeResult[1].pos_reference).toBe("O-02");

        screen.state.filter = "ONGOING";
        const ongoingResult = screen.getFilteredOrderList();
        expect(ongoingResult.length).toBe(1);
        expect(ongoingResult[0].pos_reference).toBe("O-01");

        screen.state.filter = "PAYMENT";
        const paymentResult = screen.getFilteredOrderList();
        expect(paymentResult.length).toBe(1);
        expect(paymentResult[0].pos_reference).toBe("O-02");

        screen.state.filter = "RECEIPT";
        const receiptResult = screen.getFilteredOrderList();
        expect(receiptResult.length).toBe(0);
    });

    test("search.searchTerm", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01" });
        makeOrder(store, { pos_reference: "O-02" });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.search = { fieldName: "RECEIPT_NUMBER", searchTerm: "O-01" };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    test("search.partnerId", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", partner_id: { id: 1 } });
        makeOrder(store, { pos_reference: "O-02", partner_id: { id: 2 } });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.search = { fieldName: "PARTNER", searchTerm: "", partnerId: 1 };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    test("selectedPreset", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", preset_id: { id: 10, use_timing: false } });
        makeOrder(store, { pos_reference: "O-02", preset_id: { id: 20, use_timing: false } });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.selectedPreset = { id: 10, use_timing: false };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    test("sort", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        const now = DateTime.now();
        const o1 = makeOrder(store, { pos_reference: "O-03", date_order: now }); // create 0-03 first
        const o2 = makeOrder(store, { pos_reference: "O-01", date_order: now.minus({ hours: 1 }) });
        const o3 = makeOrder(store, { pos_reference: "O-02", date_order: now });

        screen.state.filter = "ACTIVE_ORDERS";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(3);
        expect(result[0].pos_reference).toBe("O-01");
        expect(result[1].pos_reference).toBe("O-02");
        expect(result[2].pos_reference).toBe("O-03");

        screen.state.filter = "SYNCED";
        [o1, o2, o3].forEach((o) => (o.state = "paid"));
        const syncedResult = screen.getFilteredOrderList();
        expect(syncedResult.length).toBe(3);
        expect(syncedResult[0].pos_reference).toBe("O-03");
        expect(syncedResult[1].pos_reference).toBe("O-02");
        expect(syncedResult[2].pos_reference).toBe("O-01");
    });

    test("selectedPreset.use_timing", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);
        const preset = store.models["pos.preset"].get(2);

        const urgent = makeOrder(store, {
            pos_reference: "O-01",
            preset_id: preset,
        });
        const done = makeOrder(store, {
            pos_reference: "O-02",
            preset_id: preset,
        });

        screen.state.selectedPreset = preset;
        screen.state.filter = "ACTIVE_ORDERS";
        screen.orderTimers = {
            [urgent.uuid]: 30, // 30s left — not finished
            [done.uuid]: 0, // finished
        };

        const result = screen.getFilteredOrderList();
        expect(result.length).toBe(2);
        expect(result[0].pos_reference).toBe("O-01");
        expect(result[1].pos_reference).toBe("O-02");
    });

    test("pagination", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        const now = DateTime.now();
        // ACTIVE_ORDERS sorts ascending (oldest first); SYNCED/CANCELLED sort descending (newest first)
        const configs = [
            { state: "draft", prefix: "A", filter: "ACTIVE_ORDERS", page2Ref: "A-03" },
            { state: "cancel", prefix: "C", filter: "CANCELLED", page2Ref: "C-01" },
            { state: "paid", prefix: "S", filter: "SYNCED", page2Ref: "S-01" },
        ];

        for (const { state, prefix } of configs) {
            for (let i = 1; i <= 3; i++) {
                makeOrder(store, {
                    pos_reference: `${prefix}-0${i}`,
                    state,
                    date_order: now.minus({ hours: 4 - i }),
                });
            }
        }

        screen.state.nbrByPage = 2;

        for (const { filter, page2Ref } of configs) {
            screen.state.filter = filter;

            screen.state.page = 1;
            const page1 = screen.getFilteredOrderList();
            expect(page1.length).toBe(2);

            screen.state.page = 2;
            const page2 = screen.getFilteredOrderList();
            expect(page2.length).toBe(1);
            expect(page2[0].pos_reference).toBe(page2Ref);
        }
    });
});

test("isOrderDoneOrPaid", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const order = store.addNewOrder();

    order.state = "done";
    expect(screen.isOrderDoneOrPaid(order)).toBe(true);

    order.state = "paid";
    expect(screen.isOrderDoneOrPaid(order)).toBe(true);

    order.state = "draft";
    expect(screen.isOrderDoneOrPaid(order)).toBe(false);

    order.state = "cancel";
    expect(screen.isOrderDoneOrPaid(order)).toBe(false);
});

test("isOrderCancelled", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const order = store.addNewOrder();

    order.state = "cancel";
    expect(screen.isOrderCancelled(order)).toBe(true);

    order.state = "paid";
    expect(screen.isOrderCancelled(order)).toBe(false);

    order.state = "draft";
    expect(screen.isOrderCancelled(order)).toBe(false);
});

test("getStatus", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const order = makeOrder(store, { state: "cancel" });

    expect(screen.getStatus(order)).toBe("Cancelled");

    order.state = "paid";
    order.getScreenData = () => ({ name: "" });
    expect(screen.getStatus(order)).toBe("Paid");

    order.getScreenData = () => ({ name: "PaymentScreen" });
    screen.state.filter = "SYNCED";
    expect(screen.getStatus(order)).toBe("Paid");

    order.state = "draft";
    screen.state.filter = "ACTIVE_ORDERS";
    expect(screen.getStatus(order)).toBe("Payment");
});

test("_getOrderStates", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);

    store.config.set_tip_after_payment = false;
    const expectedNoTip = new Map([
        ["ACTIVE_ORDERS", { text: "Active" }],
        ["ONGOING", { text: "Ongoing", indented: true }],
        ["PAYMENT", { text: "Payment", indented: true }],
        ["CANCELLED", { text: "Cancelled" }],
    ]);
    expect(screen._getOrderStates()).toEqual(expectedNoTip);

    store.config.set_tip_after_payment = true;
    const expectedWithTip = new Map([
        ["ACTIVE_ORDERS", { text: "Active" }],
        ["ONGOING", { text: "Ongoing", indented: true }],
        ["OPEN", { text: "Open", indented: true }],
        ["TIPPING", { text: "Tipping", indented: true }],
        ["CANCELLED", { text: "Cancelled" }],
    ]);
    expect(screen._getOrderStates()).toEqual(expectedWithTip);
});

test("getStatusDecoration", async () => {
    await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);

    expect(screen.getStatusDecoration("Ongoing")).toBe("info");
    expect(screen.getStatusDecoration("Payment")).toBe("info");
    expect(screen.getStatusDecoration("Receipt")).toBe("success");
    expect(screen.getStatusDecoration("Paid")).toBe("success");
    expect(screen.getStatusDecoration("Cancelled")).toBe("danger");
    expect(screen.getStatusDecoration("anything")).toBe("secondary");
});

test("_updateSyncedOrders", async () => {
    await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);

    const capturedCalls = [];
    onRpc("pos.order", "search_order_ids", ({ kwargs }) => {
        capturedCalls.push(kwargs.state_filter);
        return { ordersInfo: [], totalCount: 0 };
    });

    screen.state.filter = "ACTIVE_ORDERS";
    await screen._updateSyncedOrders();
    expect(capturedCalls.length).toBe(0);

    screen.state.filter = "SYNCED";
    await screen._updateSyncedOrders();
    expect(capturedCalls.length).toBe(1);
    expect(capturedCalls[0]).toBe("paid");

    screen.state.filter = "CANCELLED";
    await screen._updateSyncedOrders();
    expect(capturedCalls.length).toBe(2);
    expect(capturedCalls[1]).toBe("cancelled");
});

test("isOrderSynced", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);

    // no selected order -> false
    screen.state.selectedOrderUuid = null;
    expect(screen.isOrderSynced).toBeEmpty();

    const order = store.addNewOrder();
    screen.onClickOrder(order);

    // order not completed -> false regardless of filter or screen name
    order.state = "draft";
    order.getScreenData = () => ({ name: "" });
    expect(screen.isOrderSynced).toBe(false);

    // order completed, screenData name is empty string -> true
    order.state = "paid";
    order.getScreenData = () => ({ name: "" });
    expect(screen.isOrderSynced).toBe(true);

    // order completed, filter is "SYNCED" -> true even with non-empty screen name
    order.getScreenData = () => ({ name: "PaymentScreen" });
    screen.state.filter = "SYNCED";
    expect(screen.isOrderSynced).toBe(true);

    // order completed, non-empty screen name and filter is not "SYNCED" -> false
    screen.state.filter = "ACTIVE_ORDERS";
    expect(screen.isOrderSynced).toBe(false);
});

test("refund order should not have preset_id", async () => {
    const store = await setupPosEnv();

    const normalOrder = store.createNewOrder();
    expect(Boolean(normalOrder.preset_id)).toBe(true);

    const refundOrder = store.createNewOrder({ is_refund: true });
    expect(refundOrder.preset_id).toBeEmpty();
});
