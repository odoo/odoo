import { describe, expect, test } from "@odoo/hoot";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import "@pos_event/app/models/data_service_options";

function makeOrder(state, id) {
    const order = Object.create(PosOrder.prototype);
    order.state = state;
    order.id = id;
    return order;
}

describe("pos_event data service options", () => {
    test("event registrations and answers are kept in IndexedDB for paid unsynced orders", () => {
        const options = new DataServiceOptions();
        const registrationCondition = options.databaseTable["event.registration"].condition;
        const answerCondition = options.databaseTable["event.registration.answer"].condition;
        const paidUnsyncedOrder = makeOrder("paid", "fake-uid-1234");

        expect(paidUnsyncedOrder.finalized).toBe(true);
        expect(paidUnsyncedOrder.canBeRemovedFromIndexedDB).toBe(false);

        expect(
            registrationCondition({
                pos_order_line_id: {
                    order_id: paidUnsyncedOrder,
                },
            })
        ).toBe(false);
        expect(
            answerCondition({
                registration_id: {
                    pos_order_line_id: {
                        order_id: paidUnsyncedOrder,
                    },
                },
            })
        ).toBe(false);
    });

    test("event registrations can be removed from IndexedDB for synced orders", () => {
        const options = new DataServiceOptions();
        const registrationCondition = options.databaseTable["event.registration"].condition;
        const paidSyncedOrder = makeOrder("paid", 42);

        expect(paidSyncedOrder.finalized).toBe(true);
        expect(paidSyncedOrder.canBeRemovedFromIndexedDB).toBe(true);

        expect(
            registrationCondition({
                pos_order_line_id: {
                    order_id: paidSyncedOrder,
                },
            })
        ).toBe(true);
    });

    test("event registrations can be removed from IndexedDB for cancelled orders", () => {
        const options = new DataServiceOptions();
        const registrationCondition = options.databaseTable["event.registration"].condition;
        const cancelledOrder = makeOrder("cancel", "fake-uid-5678");

        expect(cancelledOrder.canBeRemovedFromIndexedDB).toBe(true);

        expect(
            registrationCondition({
                pos_order_line_id: {
                    order_id: cancelledOrder,
                },
            })
        ).toBe(true);
    });
});
