import { test, expect, mockUserAgent } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

test("viva app payment blocked by a payment in progress on another order", async () => {
    mockUserAgent("android");
    window.localStorage.setItem("vivawallet_app_answer", "true");
    const store = await setupPosEnv();
    const viva = store.models["pos.payment.method"].get(2);
    viva.payment_provider = "viva_com";
    viva.payment_method_type = "terminal";

    const otherOrder = await getFilledOrder(store);
    createPaymentLine(store, otherOrder, viva, { payment_status: "waitingCard" });
    const order = await getFilledOrder(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    const dialogs = [];
    patchWithCleanup(comp.dialog, {
        add: (_component, props) => dialogs.push(props),
    });

    await comp.addNewPaymentLine(viva);
    expect(order.payment_ids).toHaveLength(0);
    expect(dialogs.map((d) => d.body)).toEqual([
        "There is already an electronic payment in progress.",
    ]);
});

async function setupVivaPaymentScreen({ useApp }) {
    mockUserAgent("android");
    window.localStorage.setItem("vivawallet_app_answer", String(useApp));
    const store = await setupPosEnv();
    const viva = store.models["pos.payment.method"].get(2);
    viva.payment_provider = "viva_com";
    viva.payment_method_type = "terminal";
    const order = await getFilledOrder(store);
    const line = createPaymentLine(store, order, viva, { payment_status: "waitingCard" });
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    const cancelled = [];
    patchWithCleanup(line, {
        async cancelPayment() {
            cancelled.push(this.uuid);
            return true;
        },
    });
    return { order, line, comp, cancelled };
}

test("deleting a viva terminal payment line on android cancels it on the terminal", async () => {
    const { order, line, comp, cancelled } = await setupVivaPaymentScreen({ useApp: false });
    comp.deletePaymentLine(line.uuid);
    await Promise.resolve();
    expect(cancelled).toEqual([line.uuid]);
    expect(order.payment_ids).toHaveLength(0);
});

test("deleting a viva app payment line does not send a cancel to the terminal", async () => {
    const { order, line, comp, cancelled } = await setupVivaPaymentScreen({ useApp: true });
    comp.deletePaymentLine(line.uuid);
    expect(cancelled).toEqual([]);
    expect(order.payment_ids).toHaveLength(0);
});
