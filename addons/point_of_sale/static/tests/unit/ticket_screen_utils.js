import { waitUntil } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { setupPosEnv, makeSyncedOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

const { DateTime } = luxon;

/** The ticket screen, 2 orders by page. */
export async function mountTicketScreen() {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    // Loaded, and the page refreshed after it.
    await waitUntil(() => !screen.state.loadingOrders && !screen.state.loadingPage);
    screen.state.nbrByPage = 2;
    return { store, screen };
}

/** Synced paid orders, most recent first. */
export function makePaidOrders(store, count) {
    const now = DateTime.now();
    return Array.from({ length: count }, (_, index) =>
        makeSyncedOrder(store, 1001 + index, { date_order: now.minus({ hours: index }) })
    );
}

/**
 * `search_order_ids` without filters: the page asked of the orders of the status shown.
 * The lists can be changed during the test (e.g. an order paid on another device).
 * `server.next` replaces the next answer (to delay it, lose the connection...).
 */
export function mockSearchOrderIds(store, screen, ordersByStatus) {
    const server = { calls: [], next: null };
    patch(store.data, {
        async call(model, method, args, kwargs) {
            if (method !== "search_order_ids") {
                return super.call(...arguments);
            }
            server.calls.push(kwargs);
            const orders = ordersByStatus[screen.state.filter] || [];
            const { limit, offset } = kwargs;
            const answer = {
                ordersInfo: orders
                    .slice(offset, offset + limit)
                    .map((order) => [order.id, "2000-01-01 00:00:00"]),
                totalCount: orders.length,
                offset,
            };
            const next = server.next;
            server.next = null;
            return next ? next(answer) : answer;
        },
    });
    return server;
}

export function delayNextAnswer(server) {
    const { promise, resolve } = Promise.withResolvers();
    server.next = async (answer) => {
        await promise;
        return answer;
    };
    return resolve;
}

/** The notifications of the order list; `buttons[i].onClick()` clicks a button. */
export function patchNotifications(screen) {
    const notifications = [];
    patch(screen.list.notification, {
        add(message, options) {
            notifications.push(options);
            return () => {};
        },
    });
    return notifications;
}
