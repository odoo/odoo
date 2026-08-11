import { animationFrame, click, waitFor } from "@odoo/hoot-dom";

export async function clickPaymentAction(id) {
    const button = await waitFor(
        `.paymentline_status_actions .paymentline_status_actions_button_${id}`
    );
    await click(button);
    await animationFrame();
}

export function razorpayPaymentLine(store) {
    return store
        .getOrder()
        .payment_ids.find((line) => line.payment_method_id.payment_provider === "razorpay");
}
