import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { getDeviceUuid } from "@point_of_sale/utils";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

test("getOrderlineData", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.lines).toHaveLength(2);
    expect(adapter.data.lines[0].isSelected).toBe(false);
    expect(adapter.data.lines[1].isSelected).toBe(true);
});

test("order amounts summary", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const adapter = new CustomerDisplayPosAdapter();

    adapter.formatOrderData(order);
    expectFormattedPrice(adapter.data.amount, "$ 17.85");
    expectFormattedPrice(adapter.data.amountTaxes, "$ 2.85");
    expect(adapter.data.subtotal).toBe(false);

    store.config.iface_tax_included = "subtotal";
    adapter.formatOrderData(order);
    expectFormattedPrice(adapter.data.amount, "$ 17.85");
    expectFormattedPrice(adapter.data.amountTaxes, "$ 2.85");
    expectFormattedPrice(adapter.data.subtotal, "$ 15.00");
});

test("the server is only notified while a customer display is connected", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    const updates = [];
    patchWithCleanup(store.data, {
        call(model, method, args) {
            if (model === "pos.config" && method === "update_customer_display") {
                updates.push(args);
                return Promise.resolve();
            }
            return super.call(...arguments);
        },
    });

    // No display announced itself yet: the rpc is pointless.
    adapter.dispatch(store);
    expect(updates).toHaveLength(0);

    // A display shows up, it is given the current order right away.
    store.customerDisplayAliveNotification({ device_uuid: getDeviceUuid(), needs_data: true });
    expect(updates).toHaveLength(1);

    adapter.dispatch(store);
    expect(updates).toHaveLength(2);

    // A display that already has data is only kept alive, not fed again.
    store.customerDisplayAliveNotification({ device_uuid: getDeviceUuid(), needs_data: false });
    expect(updates).toHaveLength(2);

    // A reload leaves the display blank while it is still considered connected,
    // it must be given the order back.
    store.customerDisplayAliveNotification({ device_uuid: getDeviceUuid(), needs_data: true });
    expect(updates).toHaveLength(3);

    // A display paired with another PoS must not revive ours.
    store.customerDisplayPresence.lastPing = 0;
    store.customerDisplayAliveNotification({ device_uuid: "some-other-device", needs_data: true });
    adapter.dispatch(store);
    expect(updates).toHaveLength(3);
});
