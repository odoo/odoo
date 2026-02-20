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
    const paymentline = createPaymentLine(store, order, card, { payment_status: "done" });
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

    const expectDoneAdjustAmountAction = (state) => {
        expect(normalizeActionState(state)).toEqual({
            id: "paid",
            title: "Payment Successful",
            actions: [
                {
                    id: "adjust_amount",
                    label: "Adjust Amount",
                    action: "function",
                    severity: "warning",
                },
            ],
        });
    };

    const expectDoneAction = (state) => {
        expect(normalizeActionState(state)).toEqual({
            id: "paid",
            title: "Payment Successful",
            actions: [],
        });
    };

    // Done + canBeAdjusted + amountPaid (10) < priceIncl (15)
    // --> adjust_amount action
    comp.props.isRefundOrder = false;
    paymentline.canBeAdjusted = () => true;
    order.prices.taxDetails.total_amount_no_rounding = 15;
    expectDoneAdjustAmountAction(comp.getPaymentActionState(paymentline));

    // Done + cannot be adjusted + amountPaid (10) < priceIncl (15)
    // --> paid action
    paymentline.canBeAdjusted = () => false;
    expectDoneAction(comp.getPaymentActionState(paymentline));

    // Done + canBeAdjusted + amountPaid (10) >= priceIncl (5)
    // --> paid action
    paymentline.payment_status = "done";
    order.prices.taxDetails.total_amount_no_rounding = 5;
    expectDoneAction(comp.getPaymentActionState(paymentline));
});
