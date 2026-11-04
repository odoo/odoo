import { test, expect } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { ConnectionLostError } from "@web/core/network/rpc";
import { serializeDateTime } from "@web/core/l10n/dates";
import { makeOrder, makeSyncedOrder } from "@point_of_sale/../tests/unit/utils";
import {
    makePaidOrders,
    mockSearchOrderIds,
    mountTicketScreen,
    patchNotifications,
} from "@point_of_sale/../tests/unit/ticket_screen_utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

/** Records the ids loaded; the orders not in memory yet are created as the server would send them. */
function spyLoadServerOrders(store) {
    const loadedIds = [];
    patch(store.data, {
        async loadServerOrders([[, , ids]]) {
            loadedIds.push(ids);
            return ids.map((id) => store.models["pos.order"].get(id) || makeSyncedOrder(store, id));
        },
    });
    return loadedIds;
}

test("Paid: the orders not sent yet come first, and the server is told how many", async () => {
    const { store, screen } = await mountTicketScreen();
    const now = DateTime.now();
    const notSyncedNewest = makeOrder(store, { state: "paid", date_order: now });
    const notSynced = makeOrder(store, { state: "paid", date_order: now.minus({ hours: 2 }) });
    // Synced, but with a change not sent yet: shown with the orders not synced.
    const changed = makeSyncedOrder(store, 1002, { date_order: now.minus({ hours: 2 }) });
    store.pendingOrder.write.add(changed.id);
    changed.markDirty();
    const synced = makeSyncedOrder(store, 1001, { date_order: now.minus({ hours: 1 }) });
    const server = mockSearchOrderIds(store, screen, {});
    const answer = (ordersInfo, offset) => () => ({ ordersInfo, totalCount: 2, offset });

    // Page 1 is full of orders not synced: the server sends none.
    server.next = answer([], 0);
    await screen.setFilter("SYNCED");
    expect(screen.list.orders()).toEqual([notSyncedNewest, notSynced], {
        message: "at the same date, the order not synced is the newest",
    });

    server.next = answer([[synced.id, "2000-01-01 00:00:00"]], 2);
    await screen.onNextPage();
    expect(screen.list.orders()).toEqual([changed, synced]);
    expect(
        server.calls.map(({ limit, offset, local_count }) => ({ limit, offset, local_count }))
    ).toEqual([
        { limit: 2, offset: 0, local_count: 3 },
        { limit: 2, offset: 2, local_count: 3 },
    ]);
});

test("only the orders missing or changed since are loaded", async () => {
    const { store, screen } = await mountTicketScreen();
    const now = DateTime.now();
    const product = store.models["product.template"].get(5);

    const upToDate = makeSyncedOrder(store, 1001);
    const outdated = makeSyncedOrder(store, 1002);
    // Refunded since its last change: its refund line is in memory, so it is up to date.
    const refunded = makeSyncedOrder(store, 1003, {
        state: "draft",
        write_date: now.minus({ hours: 1 }),
    });
    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, refunded);
    const refundLine = await store.addLineToOrder(
        { product_tmpl_id: product, qty: -1 },
        store.createNewOrder()
    );
    line.write_date = now.minus({ hours: 1 });
    refundLine.write_date = now;
    line.refund_orderline_ids = [refundLine.id];
    refunded.state = "paid";

    const loadedIds = spyLoadServerOrders(store);
    const server = mockSearchOrderIds(store, screen, {});
    server.next = () => ({
        ordersInfo: [
            [upToDate.id, serializeDateTime(upToDate.write_date)],
            [outdated.id, serializeDateTime(outdated.write_date.plus({ minutes: 1 }))],
            [refunded.id, serializeDateTime(now)],
            [2001, serializeDateTime(now)],
        ],
        totalCount: 4,
        offset: 0,
    });
    screen.state.nbrByPage = 4;
    await screen.setFilter("SYNCED");

    expect(loadedIds).toEqual([[outdated.id, 2001]]);
    expect(screen.list.orders().map((order) => order.id)).toEqual([1001, 1002, 1003, 2001]);
});

test("a page shown from memory is replaced only on page 1, where the newest orders come", async () => {
    const { store, screen } = await mountTicketScreen();
    spyLoadServerOrders(store);
    const [order1, order2, order3, order4] = makePaidOrders(store, 4);
    const serverOrders = [order1, order2, order3, order4];
    mockSearchOrderIds(store, screen, { SYNCED: serverOrders });
    const shownIds = () => screen.list.orders().map((order) => order.id);

    await screen.setFilter("SYNCED");
    await screen.onNextPage();

    // An order is paid on another device: page 1, seen before, shows at once then is replaced.
    serverOrders.unshift({ id: 2001 });
    const goingBack = screen.onPrevPage();
    expect(shownIds()).toEqual([order1.id, order2.id]);
    await goingBack;
    expect(shownIds()).toEqual([2001, order1.id]);

    await screen.onNextPage();
    await screen.onPrevPage();
    expect(shownIds()).toEqual([2001, order1.id]);

    // Another one: page 2, seen before, doesn't move under the user...
    serverOrders.unshift({ id: 2002 });
    await screen.onNextPage();
    expect(shownIds()).toEqual([order2.id, order3.id]);
    // ... but the other pages are fetched again.
    await screen.onPrevPage();
    expect(shownIds()).toEqual([2002, 2001]);
});

test("refresh fetches the page again, on the focused order while the user stays on it", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 5);
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });
    const lastCall = () => {
        const { focus_order_id, offset } = server.calls.at(-1);
        return { focus_order_id, offset };
    };

    // The server gives the page of the focused order (the 5th order: page 3).
    server.next = (answer) => ({
        ...answer,
        ordersInfo: [[orders[4].id, "2000-01-01 00:00:00"]],
        offset: 4,
    });
    await screen.setFilter("SYNCED", { focusOrderId: orders[4].id });
    await screen.list.refresh();
    expect(lastCall()).toEqual({ focus_order_id: orders[4].id, offset: 4 });

    await screen.onPrevPage();
    await screen.list.refresh();
    expect(lastCall()).toEqual({ focus_order_id: false, offset: 2 });
});

test("connection lost while the filters change: page 1 from memory", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 3);
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });

    server.next = () => {
        throw new ConnectionLostError("/web/dataset/call_kw");
    };
    await screen.setFilter("SYNCED");

    expect(screen.list.isLocalPage).toBe(true);
    expect(screen.list.orders()).toEqual(orders.slice(0, 2));
});

test("'Offline mode' does nothing once the filters changed", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 3);
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });
    const notifications = patchNotifications(screen);
    await screen.setFilter("SYNCED");

    server.next = () => {
        throw new ConnectionLostError("/web/dataset/call_kw");
    };
    await screen.onNextPage();
    await screen.setFilter("CANCELLED");
    notifications[0].buttons[0].onClick();

    expect(screen.list.isLocalPage).toBe(false);
    expect(screen.state.filter).toBe("CANCELLED");
    expect(screen.state.page).toBe(1);
});

test("connection lost on a page past the orders in memory: their last page", async () => {
    const { store, screen } = await mountTicketScreen();
    const [focusedOrder] = makePaidOrders(store, 1);
    const server = mockSearchOrderIds(store, screen, {});

    // Scanned: the server opens its page (page 3), the pages before were never loaded.
    server.next = () => ({
        ordersInfo: [[focusedOrder.id, "2000-01-01 00:00:00"]],
        totalCount: 5,
        offset: 4,
    });
    await screen.setFilter("SYNCED", { focusOrderId: focusedOrder.id });
    expect(screen.state.page).toBe(3);

    server.next = () => {
        throw new ConnectionLostError("/web/dataset/call_kw");
    };
    await screen.list.refresh();
    expect(screen.list.isLocalPage).toBe(true);
    expect(screen.state.page).toBe(1);
    expect(screen.list.orders()).toEqual([focusedOrder]);
});
