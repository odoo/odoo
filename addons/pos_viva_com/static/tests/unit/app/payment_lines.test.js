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
import { isVivaAppEnabled, setVivaAppEnabled } from "@pos_viva_com/app/utils/viva_app";

definePosModels();

test("getPaymentActionState", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "waitingCard" });
    const deletedLines = [];
    const comp = await mountWithCleanup(PaymentScreenPaymentLines, {
        props: {
            paymentLines: [paymentline],
            deleteLine: (uuid) => deletedLines.push(uuid),
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

    // Viva app used on this device
    setVivaAppEnabled(true);
    comp.vivaApp = { use: () => true };
    const appState = comp.getPaymentActionState(paymentline);
    appState.actions[0].action();
    expect(deletedLines).toEqual([paymentline.uuid]);
    expect(isVivaAppEnabled()).toBe(false);
    expect(normalizeActionState(appState)).toEqual({
        id: "viva_continue_app",
        title: "Continue on Viva app",
        icon: "smartphone",
        actions: [
            {
                id: "viva_use_terminal",
                label: "Use terminal instead",
                title: "Stop using the Viva app on this device",
                action: "function",
                severity: "warning",
            },
        ],
    });

    // Viva app not used: regular terminal flow, no Viva app action
    comp.vivaApp = { use: () => false };
    expect(normalizeActionState(comp.getPaymentActionState(paymentline))).toEqual({
        id: "waiting_card",
        icon: "autorenew",
        iconClass: "oi-spin",
        title: "Waiting for card",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
                show: true,
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
