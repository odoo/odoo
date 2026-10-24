import { test, expect, describe, waitFor, waitForNone, mockDate } from "@odoo/hoot";
import { getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { click, animationFrame } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { session } from "@web/session";
import { BarcodePlugin } from "@barcodes/barcode_plugin";
import { setupPosEnv, makeOrder, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
const { DateTime } = luxon;
import * as Utils from "../ui_utils";

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
    await Utils.selectTicketFilter("Paid");
    await waitFor(".info-column");
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(comboLine.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "2" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "3" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});

test("Clicking Edit Payment closes OrderDetailsDialog and navigates to PaymentScreen", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cashPaymentMethod = store.models["pos.payment.method"].get(1);
    order.state = "paid";
    order.addPaymentline(cashPaymentMethod);

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen._onInfoOrder(order);
    await waitFor(".o_dialog");
    await click('[data-icon="edit"]');
    await waitForNone(".o_dialog");
    expect(order.getScreenData().name).toBe("PaymentScreen");
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
        mockDate("2026-05-15 12:00:00");
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
        expect(syncedResult[0].pos_reference).toBe("O-01");
        expect(syncedResult[1].pos_reference).toBe("O-02");
        expect(syncedResult[2].pos_reference).toBe("O-03");
    });

    test("sort by preset time or order date: today, upcoming, then past", async () => {
        mockDate("2026-05-15 12:00:00");
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);
        const preset = store.models["pos.preset"].get(2);

        const now = DateTime.now();
        const orders = [
            // Placed yesterday for today
            {
                pos_reference: "O-01",
                date_order: now.minus({ days: 1 }),
                preset_time: now.plus({ hours: 2 }),
            },
            // Placed today for tomorrow
            { pos_reference: "O-02", date_order: now, preset_time: now.plus({ days: 1 }) },
            // Placed today without preset time
            { pos_reference: "O-03", date_order: now.minus({ hours: 1 }), preset_time: false },
            // Placed two days ago for yesterday
            {
                pos_reference: "O-04",
                date_order: now.minus({ days: 2 }),
                preset_time: now.minus({ days: 1 }),
            },
            // Placed three days ago
            { pos_reference: "O-05", date_order: now.minus({ days: 3 }), preset_time: false },
            // Placed today for in two days
            { pos_reference: "O-06", date_order: now, preset_time: now.plus({ days: 2 }) },
        ].map((vals) => makeOrder(store, { ...vals, preset_id: preset }));
        // In each day group, orders with a preset time come before those without
        const expected = ["O-01", "O-03", "O-02", "O-06", "O-04", "O-05"];

        screen.state.filter = "ACTIVE_ORDERS";
        expect(screen.getFilteredOrderList().map((o) => o.pos_reference)).toEqual(expected);

        screen.state.selectedPreset = preset;
        expect(screen.getFilteredOrderList().map((o) => o.pos_reference)).toEqual(expected);

        screen.state.selectedPreset = null;
        screen.state.filter = "SYNCED";
        orders.forEach((o) => (o.state = "paid"));
        expect(screen.getFilteredOrderList().map((o) => o.pos_reference)).toEqual(expected);
    });

    test("pagination", async () => {
        mockDate("2026-05-15 12:00:00");
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        const now = DateTime.now();
        // Today's orders are sorted ascending (oldest first) for every filter
        const configs = [
            { state: "draft", prefix: "A", filter: "ACTIVE_ORDERS", page2Ref: "A-03" },
            { state: "cancel", prefix: "C", filter: "CANCELLED", page2Ref: "C-03" },
            { state: "paid", prefix: "S", filter: "SYNCED", page2Ref: "S-03" },
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

test("showSubPads", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    await animationFrame();
    expect(document.querySelectorAll(".subpads").length).toBe(0);
    order.state = "paid";
    ticketScreen.onClickOrder(order);
    await animationFrame();
    expect(store.accessRight.canShowPads).toBe(true);
});

test("showInvoiceButton", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.showInvoiceButton).toBe(false);
    order.state = "paid";
    expect(ticketScreen.showInvoiceButton).toBe(true);
});

// Preset 1 ("In") is the config default and carries fiscal position 1, mapped here to
// turn the 15% tax into the 25% one. Preset 2 ("Out") has no fiscal position.
const setupPresetFiscalPositions = (store) => {
    const mappedFp = store.models["account.fiscal.position"].get(1);
    mappedFp.update({ tax_map: { 1: [2] } });
    return {
        presetWithFp: store.models["pos.preset"].get(1),
        presetWithoutFp: store.models["pos.preset"].get(2),
        mappedFp,
    };
};

const getPaidOrder = async (store, { preset, fiscalPosition }) => {
    const order = store.addNewOrder({ preset_id: preset });
    order.fiscal_position_id = fiscalPosition;
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 2 },
        order
    );
    order.state = "paid";
    return order;
};

const refundOrder = async (comp, order) => {
    comp.setSelectedOrder(order);
    for (const line of order.lines) {
        comp.getToRefundDetail(line).qty = line.qty;
    }
    await comp.onDoRefund();
    return comp.pos.getOrder();
};

const appliedTaxIds = (line) =>
    line.prepareBaseLineForTaxesComputationExtraValues().tax_ids.map((tax) => tax.id);

test("refund keeps the fiscal position of the refunded order, not the default preset one", async () => {
    const store = await setupPosEnv();
    const { presetWithFp, presetWithoutFp, mappedFp } = setupPresetFiscalPositions(store);
    expect(store.config.default_preset_id.id).toBe(presetWithFp.id);

    const order = await getPaidOrder(store, { preset: presetWithoutFp, fiscalPosition: false });
    expect(order.priceIncl).toBe(230);

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    const refund = await refundOrder(comp, order);

    expect(refund.is_refund).toBe(true);
    expect(refund.fiscal_position_id?.id).toBe(undefined, {
        message: "the refund must not inherit the fiscal position of the default preset",
    });
    expect(appliedTaxIds(refund.lines[0])).toEqual([1]);
    expect(refund.priceIncl).toBe(-230);
    expect(mappedFp.tax_map[1]).toEqual([2]);
    // Sent explicitly, otherwise _complete_values_from_session falls back to the config default.
    expect(store.models.serializeForORM(refund).fiscal_position_id).toBe(false);
});

test("refund keeps the fiscal position of the refunded order when the default preset has none", async () => {
    const store = await setupPosEnv();
    const { presetWithFp, presetWithoutFp, mappedFp } = setupPresetFiscalPositions(store);
    store.config.default_preset_id = presetWithoutFp;

    const order = await getPaidOrder(store, { preset: presetWithFp, fiscalPosition: mappedFp });
    expect(order.priceIncl).toBe(250);

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    const refund = await refundOrder(comp, order);

    expect(refund.fiscal_position_id?.id).toBe(mappedFp.id);
    expect(appliedTaxIds(refund.lines[0])).toEqual([2]);
    expect(refund.priceIncl).toBe(-250);
});

test("scanning a barcode on the ticket screen does not feed the refund quantity", async () => {
    // The buffer only drops fast multi-key sequences outside of test mode.
    patch(session, { test_mode: false });

    const store = await setupPosEnv();
    const order = store.addNewOrder({});
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 10 },
        order
    );
    order.state = "paid";
    const line = order.lines[0];

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    comp.setSelectedOrder(order);
    comp.state.selectedOrderlineIds[order.id] = line.id;

    const dialogTitles = [];
    patch(comp.dialog, {
        add: (_component, props) => dialogTitles.push(props.title.toString()),
    });

    // A scanner types the barcode a few ms per character.
    for (const char of "5901234123457") {
        window.dispatchEvent(new KeyboardEvent("keyup", { key: char }));
        await advanceTime(10);
    }
    await advanceTime(BarcodePlugin.maxTimeBetweenKeysInMs);

    expect(comp.getToRefundDetail(line).qty).toBe(0);
    expect(dialogTitles).toEqual([]);
});

test("searching by customer keeps the orders of a nameless address contact", async () => {
    const store = await setupPosEnv();
    const company = store.models["res.partner"].get(3);
    const address = store.models["res.partner"].create({
        name: false,
        parent_name: company.name,
    });
    const companyOrder = store.addNewOrder({ partner_id: company });
    const addressOrder = store.addNewOrder({ partner_id: address });
    expect(addressOrder.getPartnerName()).toBe(company.name);

    const comp = await mountWithCleanup(TicketScreen, {
        props: { stateOverride: { search: { fieldName: "PARTNER", searchTerm: company.name } } },
    });
    expect(comp.getFilteredOrderList().map((order) => order.id)).toEqual(
        [companyOrder.id, addressOrder.id],
        { message: "the address contact is searched by its company name" }
    );
});

test("onClickScanOrder selects the filter matching the finalized order state and resets the list", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const preset = store.models["pos.preset"].get(2);
    onRpc("pos.order", "search_order_ids", () => ({ ordersInfo: [], totalCount: 0 }));
    screen.state.nbrByPage = 30;

    const cases = [
        { state: "paid", screenName: "", filter: "SYNCED" },
        { state: "done", screenName: "", filter: "SYNCED" },
        { state: "paid", screenName: "TipScreen", filter: "ACTIVE_ORDERS" },
        { state: "cancel", screenName: "", filter: "CANCELLED" },
    ];
    for (const { state, screenName, filter } of cases) {
        const order = makeOrder(store, {
            state,
            getScreenData: () => ({ name: screenName }),
        });
        patch(store.data, { loadServerOrders: async () => [order] });

        screen.state.filter = null;
        screen.state.selectedPreset = preset;
        screen.state.search = { fieldName: "RECEIPT_NUMBER", searchTerm: "foo" };
        screen.state.page = 2;
        await animationFrame();
        expect(".pos-search-bar input").toHaveValue("foo");

        // The camera scanner is open while scanning, and closed once the order is found
        store.scanning = true;
        await screen.onClickScanOrder(`http://localhost/?order_uuid=${order.uuid}`);
        await animationFrame();

        expect(store.scanning).toBe(false);

        expect(screen.state.filter).toBe(filter);
        expect(screen.getSelectedOrder()).toBe(order);
        expect(screen.state.selectedPreset).toBe(null);
        expect(screen.state.search).toEqual({ fieldName: "RECEIPT_NUMBER", searchTerm: "" });
        expect(screen.state.page).toBe(1);
        expect(".pos-search-bar input").toHaveValue("");
        expect(screen.getFilteredOrderList()).toInclude(order);
    }
});

test("onClickScanOrder displays the page holding the scanned order", async () => {
    mockDate("2026-05-15 12:00:00");
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    screen.state.nbrByPage = 2;

    onRpc("pos.order", "search_order_ids", () => ({ ordersInfo: [], totalCount: 0 }));

    const now = DateTime.now();
    const orders = [1, 2, 3].map((i) =>
        makeOrder(store, {
            state: "paid",
            pos_reference: `O-0${i}`,
            date_order: now.minus({ hours: 4 - i }),
            getScreenData: () => ({ name: "" }),
        })
    );
    const scannedOrder = orders[2];
    patch(store.data, { loadServerOrders: async () => [scannedOrder] });

    store.scanning = true;
    await screen.onClickScanOrder(`http://localhost/?order_uuid=${scannedOrder.uuid}`);

    expect(screen.state.filter).toBe("SYNCED");
    expect(screen.state.page).toBe(2);
    expect(screen.getFilteredOrderList()).toInclude(scannedOrder);
    expect(screen.getSelectedOrder()).toBe(scannedOrder);
});

test("onClickScanOrder loads a draft order directly", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const order = makeOrder(store);
    store.addNewOrder();
    patch(store.data, { loadServerOrders: async () => [order] });

    store.scanning = true;
    await screen.onClickScanOrder(`http://localhost/?order_uuid=${order.uuid}`);

    expect(store.scanning).toBe(false);
    expect(store.getOrder()).toBe(order);
});

test("onClickScanOrder warns without loading when the qr code holds no order", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    let loadCount = 0;
    patch(store.data, { loadServerOrders: async () => ++loadCount && [] });
    const notifications = [];
    patch(getService("notification"), {
        add: (message) => notifications.push(message.toString()),
    });

    await screen.onClickScanOrder("http://localhost/?foo=bar");
    await screen.onClickScanOrder("not a url");

    expect(loadCount).toBe(0);
    expect(notifications).toEqual([
        "Invalid QR Code! Please, Scan again!",
        "Invalid QR Code! Please, Scan again!",
    ]);
});

test("scanning an order qr code with a barcode scanner retrieves the order", async () => {
    patch(session, { nomenclature_id: 1 });
    await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const scannedCodes = [];
    patch(screen, { onClickScanOrder: (qrcode) => scannedCodes.push(qrcode) });

    const qrcode = "http://localhost/?order_uuid=abc";
    await Utils.scanBarcode(qrcode);

    expect(scannedCodes).toEqual([qrcode]);
});

test("onSearch retrieves the order of a qr code typed in the search bar", async () => {
    await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const scannedCodes = [];
    let searchCount = 0;
    patch(screen, {
        onClickScanOrder: (qrcode) => scannedCodes.push(qrcode),
        _updateSyncedOrders: async () => searchCount++,
    });

    // Barcode scanners type into the focused search bar
    const qrcode = "http://localhost/?order_uuid=abc";
    await screen.onSearch({ fieldName: "RECEIPT_NUMBER", searchTerm: qrcode });
    expect(scannedCodes).toEqual([qrcode]);
    expect(searchCount).toBe(0);
    expect(screen.state.search.searchTerm).not.toBe(qrcode);

    await screen.onSearch({ fieldName: "RECEIPT_NUMBER", searchTerm: "O-01" });
    expect(scannedCodes).toEqual([qrcode]);
    expect(searchCount).toBe(1);
    expect(screen.state.search).toEqual({ fieldName: "RECEIPT_NUMBER", searchTerm: "O-01" });
});
