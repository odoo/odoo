import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { ONLINE_PAYMENT_METHOD_ID } from "@pos_online_payment/../tests/unit/data/pos_payment_method.data";

definePosModels();

describe("delete button", () => {
    test("Uses an online accounting payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        order.uiState.selected_paymentline_uuid = paymentline.uuid;
        paymentline.online_account_payment_id = 1;

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline button.delete-button").toHaveCount(0);
    });

    test("Do not use an online accounting payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        order.uiState.selected_paymentline_uuid = paymentline.uuid;
        paymentline.online_account_payment_id = false;

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline button.delete-button").toHaveCount(1);
    });
});

test("edit payment of an order paid with online payment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const online = store.models["pos.payment.method"].get(ONLINE_PAYMENT_METHOD_ID);
    const card = store.models["pos.payment.method"].get(2);
    createPaymentLine(store, order, online, { online_account_payment_id: 1 });
    order.state = "paid";
    // Only online payments: nothing could be edited
    expect(order.canEditPayment).toBe(false);

    // The card payment can be edited, the online one stays as is
    createPaymentLine(store, order, card);
    expect(order.canEditPayment).toBe(true);

    // A printed order can't be refunded and copied with its online payment
    order.nb_print = 1;
    expect(order.canEditPayment).toBe(false);
    expect(store.canEditPayment(order)).toBe(false);
});
