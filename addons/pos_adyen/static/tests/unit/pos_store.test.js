import { expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc } from "@web/../tests/web_test_helpers";
// Side-effect import: applies the PosStore patch under test.
import "@pos_adyen/app/services/pos_store";

definePosModels();

const adyenNotification = (serviceId, result = "Success") => ({
    SaleToPOIResponse: {
        MessageHeader: { ServiceID: serviceId },
        PaymentResponse: {
            Response: {
                AdditionalResponse: "pspReference=PSP123",
                Result: result,
            },
        },
    },
});

const setupStore = async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "adyen"
    );
    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push({ component, props });
    return { store, order, paymentMethod, dialogs };
};

test("alerts when a successful notification matches no local payment line", async () => {
    const { store, paymentMethod, dialogs } = await setupStore();
    onRpc("pos.payment.method", "get_latest_adyen_status", () =>
        adyenNotification("orphan-service-id")
    );

    await store._checkOrphanedAdyenNotification(paymentMethod);

    expect(dialogs.length).toBe(1);
    expect(String(dialogs[0].props.title)).toBe("Unmatched Adyen payment");
    expect(String(dialogs[0].props.body)).toInclude("PSP123");
});

test("does not alert when a local line already knows this service id (bus replay)", async () => {
    const { store, order, paymentMethod, dialogs } = await setupStore();
    const line = order.addPaymentline(paymentMethod).data;
    line.setTerminalServiceId("already-seen");
    // Already handled earlier through some other path (done, retry, ...);
    // the replayed notification must not re-trigger the alert.
    line.setPaymentStatus("retry");
    onRpc("pos.payment.method", "get_latest_adyen_status", () => adyenNotification("already-seen"));

    await store._checkOrphanedAdyenNotification(paymentMethod);

    expect(dialogs.length).toBe(0);
});

test("does not alert when the buffer is empty", async () => {
    const { store, paymentMethod, dialogs } = await setupStore();
    onRpc("pos.payment.method", "get_latest_adyen_status", () => false);

    await store._checkOrphanedAdyenNotification(paymentMethod);

    expect(dialogs.length).toBe(0);
});

test("does not alert for a definitive failure with no pending line", async () => {
    const { store, paymentMethod, dialogs } = await setupStore();
    onRpc("pos.payment.method", "get_latest_adyen_status", () =>
        adyenNotification("orphan-service-id", "Failure")
    );

    await store._checkOrphanedAdyenNotification(paymentMethod);

    expect(dialogs.length).toBe(0);
});
