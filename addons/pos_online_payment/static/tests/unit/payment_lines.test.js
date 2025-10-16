import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

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
