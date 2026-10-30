import { test, expect } from "@odoo/hoot";
import { MockServer, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("clickPrintBill syncs the order so it isn't lost on a data reload", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    patchWithCleanup(store.ticketPrinter, {
        async generateIframe() {
            return document.createElement("iframe");
        },
        async generateImage() {
            return "fake_image_data";
        },
        print() {
            return { successful: true };
        },
        printWeb() {},
    });

    const component = await mountWithCleanup(ControlButtons, {});
    expect(order.isSynced).toBe(false);

    await component.clickPrintBill();

    expect(order.isSynced).toBe(true);
    expect(order.isDirty()).toBe(false);
    expect(store.getPendingOrder().orderToCreate).toHaveLength(0);
});

test("clickPrintBill prints the lines added by another device", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();
    let printedQty;
    patchWithCleanup(store.ticketPrinter, {
        async printOrderReceipt({ order }) {
            printedQty = order.lines.map((line) => line.qty);
        },
    });

    // Another device adds a line without this one being notified
    MockServer.env["pos.order"].write([order.id], {
        lines: [[0, 0, { product_id: order.lines[1].product_id.id, price_unit: 10, qty: 7 }]],
    });
    const component = await mountWithCleanup(ControlButtons, {});
    await component.clickPrintBill();

    expect(printedQty).toEqual([3, 2, 7]);
});
