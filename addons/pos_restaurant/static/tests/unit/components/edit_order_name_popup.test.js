import { expect, test } from "@odoo/hoot";
import { EditOrderNamePopup } from "@pos_restaurant/app/components/popup/edit_order_name_popup/edit_order_name_popup";

test("selecting an existing order waits for the transfer before closing the popup", async () => {
    const transfer = Promise.withResolvers();
    const destination = { uuid: "destination" };
    const calls = [];
    const popup = {
        currentOrder: { uuid: "source" },
        pos: {
            transferOrder(uuid, table, order) {
                expect([uuid, table, order]).toEqual(["source", null, destination]);
                return transfer.promise;
            },
            setOrder(order) {
                expect(order).toBe(destination);
                calls.push("select destination");
            },
        },
        dialog: { closeAll: () => calls.push("close popup") },
        ui: {
            block: () => calls.push("block UI"),
            unblock: () => calls.push("unblock UI"),
        },
    };

    const pending = EditOrderNamePopup.prototype.transferOrder.call(popup, destination);
    expect(calls.filter((call) => call !== "block UI")).toEqual([]);
    transfer.resolve();
    await pending;
    expect(calls).toEqual(["block UI", "select destination", "close popup", "unblock UI"]);
});
