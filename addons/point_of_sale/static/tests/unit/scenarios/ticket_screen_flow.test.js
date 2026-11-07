import { test, expect } from "@odoo/hoot";
import { ConnectionLostError } from "@web/core/network/rpc";
import { makeOrder, makeSyncedOrder } from "@point_of_sale/../tests/unit/utils";
import {
    delayNextAnswer,
    makePaidOrders,
    mockSearchOrderIds,
    mountTicketScreen,
    patchNotifications,
} from "@point_of_sale/../tests/unit/ticket_screen_utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

test("Paid: next and previous pages, a page already seen shows at once", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 5);
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });

    await screen.setFilter("SYNCED");
    expect(screen.list.orders()).toEqual(orders.slice(0, 2));
    await screen.onNextPage();
    expect(screen.list.orders()).toEqual(orders.slice(2, 4));

    // Back to page 1: shown before the server answers, then checked with it.
    const answer = delayNextAnswer(server);
    const goingBack = screen.onPrevPage();
    expect(screen.list.orders()).toEqual(orders.slice(0, 2));
    expect(screen.state.loadingPage).toBe(false);
    answer();
    await goingBack;
    expect(screen.list.orders()).toEqual(orders.slice(0, 2));

    await screen.onNextPage();
    await screen.onNextPage();
    expect(screen.list.orders()).toEqual(orders.slice(4));
    await screen.onNextPage();
    expect(server.calls.map(({ offset }) => offset)).toEqual([0, 2, 0, 2, 4], {
        message: "no page asked after the last one",
    });
});

test("Paid: a late answer doesn't replace the list shown since", async () => {
    const { store, screen } = await mountTicketScreen();
    const paidOrders = makePaidOrders(store, 3);
    const cancelledOrder = makeSyncedOrder(store, 2001, { state: "cancel" });
    const server = mockSearchOrderIds(store, screen, {
        SYNCED: paidOrders,
        CANCELLED: [cancelledOrder],
    });
    await screen.setFilter("SYNCED");

    const answer = delayNextAnswer(server);
    const nextPage = screen.onNextPage();
    expect(screen.state.loadingPage).toBe(true, { message: "a page not seen yet looks busy" });
    await screen.setFilter("CANCELLED");
    answer();
    await nextPage;

    expect(screen.state.page).toBe(1);
    expect(screen.list.orders()).toEqual([cancelledOrder]);
});

test("Paid offline: the orders in memory, then the server's once back online", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 3);
    const notSynced = makeOrder(store, {
        state: "paid",
        date_order: DateTime.now().minus({ days: 1 }),
    });
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });

    store.data.network.offline = true;
    await screen.setFilter("SYNCED");
    expect(screen.list.isLocalPage).toBe(true);
    expect(screen.list.orders()).toEqual([notSynced, orders[0]], {
        message: "the order not synced comes first, even if older",
    });
    await screen.onNextPage();
    expect(screen.list.orders()).toEqual(orders.slice(1));
    expect(server.calls).toEqual([]);

    store.data.network.offline = false;
    expect(screen.list.showReloadBanner).toBe(true);
    // The server leaves room for the order not synced.
    server.next = (answer) => ({ ...answer, ordersInfo: answer.ordersInfo.slice(0, 1) });
    await screen.list.reload();
    expect(screen.list.isLocalPage).toBe(false);
    expect(screen.list.orders()).toEqual([notSynced, orders[0]]);
    expect(server.calls).toHaveLength(1);
});

test("Paid: connection lost while changing page, the page can be shown from memory", async () => {
    const { store, screen } = await mountTicketScreen();
    const orders = makePaidOrders(store, 3);
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });
    const notifications = patchNotifications(screen);
    await screen.setFilter("SYNCED");

    server.next = () => {
        throw new ConnectionLostError("/web/dataset/call_kw");
    };
    await screen.onNextPage();
    expect(screen.list.orders()).toEqual(orders.slice(0, 2), { message: "the page shown stays" });
    expect(notifications).toHaveLength(1);

    notifications[0].buttons[0].onClick(); // "Offline mode"
    expect(screen.list.isLocalPage).toBe(true);
    expect(screen.state.page).toBe(2);
    expect(screen.list.orders()).toEqual(orders.slice(2));
});

test("a scanned order opens on its status and page", async () => {
    const { store, screen } = await mountTicketScreen();
    const now = DateTime.now();
    const activeOrders = [1, 2, 3].map((index) =>
        makeOrder(store, {
            pos_reference: `00${index}`,
            date_order: now.minus({ hours: 4 - index }),
        })
    );
    const paidOrder = makeSyncedOrder(store, 1005);
    const server = mockSearchOrderIds(store, screen, {});
    await screen.setFilter("SYNCED");
    screen.state.search = { fieldName: "RECEIPT_NUMBER", searchTerm: "another order" };

    await screen.selectScannedOrder(activeOrders[2]);
    expect(screen.state.filter).toBe("ACTIVE_ORDERS");
    expect(screen.state.page).toBe(2);
    expect(screen.state.search.searchTerm).toBe("", { message: "the search is cleared" });
    expect(screen.state.selectedOrderUuid).toBe(activeOrders[2].uuid);

    // The server gives the page of the order (the 5th order: page 3).
    server.next = () => ({
        ordersInfo: [[paidOrder.id, "2000-01-01 00:00:00"]],
        totalCount: 5,
        offset: 4,
    });
    await screen.selectScannedOrder(paidOrder);
    expect(server.calls.at(-1).focus_order_id).toBe(paidOrder.id);
    expect(screen.state.filter).toBe("SYNCED");
    expect(screen.state.page).toBe(3);
    expect(screen.list.orders()).toEqual([paidOrder]);
});
