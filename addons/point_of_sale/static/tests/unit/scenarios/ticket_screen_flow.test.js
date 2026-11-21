import { after, test, expect } from "@odoo/hoot";
import { animationFrame, waitUntil } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { ConnectionLostError } from "@web/core/network/rpc";
import { makeOrder, makeSyncedOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import {
    delayNextAnswer,
    makePaidOrders,
    mockSearchOrderIds,
    mountRoutedTicketScreen,
    mountTicketScreen,
    patchNotifications,
} from "@point_of_sale/../tests/unit/ticket_screen_utils";
import { TicketOrderList } from "@point_of_sale/app/screens/ticket_screen/ticket_order_list";
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
    expect(screen.list.pageState.loadingPage).toBe(false);
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
    expect(screen.list.pageState.loadingPage).toBe(true, {
        message: "a page not seen yet looks busy",
    });
    await screen.setFilter("CANCELLED");
    answer();
    await nextPage;

    expect(screen.list.pageState.page).toBe(1);
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
    await screen.list.reload();
    expect(screen.list.isLocalPage).toBe(false);
    expect(screen.list.orders()).toEqual([notSynced, orders[0]]);
    expect(server.calls.map(({ limit, offset }) => ({ limit, offset }))).toEqual(
        [{ limit: 1, offset: 0 }],
        { message: "the server leaves room for the order not synced" }
    );
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
    expect(screen.list.pageState.page).toBe(2);
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
    const serverOrders = {};
    const server = mockSearchOrderIds(store, screen, serverOrders);
    await screen.setFilter("SYNCED");
    screen.state.search = { fieldName: "RECEIPT_NUMBER", searchTerm: "another order" };

    await screen.selectScannedOrder(activeOrders[2]);
    expect(screen.state.filter).toBe("ACTIVE_ORDERS");
    expect(screen.list.pageState.page).toBe(2);
    expect(screen.state.search.searchTerm).toBe("", { message: "the search is cleared" });
    expect(screen.state.selectedOrderUuid).toBe(activeOrders[2].uuid);

    // The server gives the index of the order (the 5th order: page 3), then its page.
    serverOrders.SYNCED = [...[2001, 2002, 2003, 2004].map((id) => ({ id })), paidOrder];
    await screen.selectScannedOrder(paidOrder);
    expect(
        server.calls.slice(-2).map(({ focus_order_id, offset }) => ({ focus_order_id, offset }))
    ).toEqual([
        { focus_order_id: paidOrder.id, offset: 0 },
        { focus_order_id: false, offset: 4 },
    ]);
    expect(screen.state.filter).toBe("SYNCED");
    expect(screen.list.pageState.page).toBe(3);
    expect(screen.list.orders()).toEqual([paidOrder]);
});

test("the orders are loaded once for the screens opened meanwhile, a closed screen isn't refreshed", async () => {
    const store = await setupPosEnv();
    const loading = Promise.withResolvers();
    let loads = 0;
    patch(store, {
        getServerOrders() {
            loads++;
            return loading.promise;
        },
    });
    let refreshes = 0;
    // A class patch is kept by the next tests: removed after this one.
    after(
        patch(TicketOrderList.prototype, {
            refresh() {
                refreshes++;
                return super.refresh(...arguments);
            },
        })
    );

    // Closed and opened again while the orders load.
    const { router } = await mountRoutedTicketScreen();
    router.page.shown = false;
    await animationFrame();
    router.page.shown = true;
    await animationFrame();
    expect(loads).toBe(1);

    loading.resolve();
    await waitUntil(() => !store.loadingOrderState);
    expect(refreshes).toBe(0, { message: "the screen that loaded the orders is closed" });

    // Opened once loaded: the screen loads the orders, then refreshes its page.
    router.page.shown = false;
    await animationFrame();
    router.page.shown = true;
    await waitUntil(() => refreshes === 1);
    expect(loads).toBe(2);
});

test("a navigation without state props keeps the page and the filters", async () => {
    const store = await setupPosEnv();
    const orders = makePaidOrders(store, 5);
    const { router, getScreen } = await mountRoutedTicketScreen();
    await waitUntil(() => !store.loadingOrderState);
    const screen = getScreen();
    const server = mockSearchOrderIds(store, screen, { SYNCED: orders });

    // E.g. the order tracker, while the screen is open: applied and fetched.
    router.page.params = { stateOverride: { filter: "SYNCED", nbrByPage: 2 } };
    await waitUntil(() => server.calls.length === 1 && !screen.list.pageState.loadingPage);
    await screen.onNextPage();
    await screen.onNextPage();
    expect(screen.list.pageState.page).toBe(3);

    // E.g. the scanner turned on: the same screen, without props.
    router.page.params = {};
    await animationFrame();
    expect(getScreen()).toBe(screen);
    expect(screen.state.filter).toBe("SYNCED");
    expect(screen.list.pageState.page).toBe(3);
    expect(server.calls).toHaveLength(3);
});
