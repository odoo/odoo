import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    setupPosEnv,
    getFilledOrder,
    createPaymentLine,
    normalizeFunctionsInObject,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

definePosModels();

test("getPaymentActionState", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "waitingCard" });
    const comp = await mountWithCleanup(PaymentScreenPaymentLines, {
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

    // Helper
    const normalizeActionState = (state) => {
        state.actions = state.actions.map(normalizeFunctionsInObject);
        return state;
    };

    // Mock vivaApp integration
    comp.vivaApp = { isIntegrated: () => true };
    expect(normalizeActionState(comp.getPaymentActionState(paymentline))).toEqual({
        id: "viva_continue_app",
        title: "Continue on Viva app",
        icon: "fa fa-mobile",
        actions: [
            {
                id: "viva_reset_integration",
                label: "Reset Integration",
                title: "Reset Viva Integration",
                action: "function",
                severity: "danger",
            },
        ],
    });

    // Mock vivaApp non-integration
    comp.vivaApp = { isIntegrated: () => false };
    expect(normalizeActionState(comp.getPaymentActionState(paymentline))).toEqual({
        id: "waiting_card",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Waiting for card",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
            },
            {
                id: "cancel",
                label: "Cancel",
                title: "Send Cancel Request",
                action: "function",
                severity: "danger",
                show: true,
            },
        ],
    });
});
