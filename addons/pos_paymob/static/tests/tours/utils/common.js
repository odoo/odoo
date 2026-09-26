/* global posmodel */

// There is no terminal in a tour, so we post Paymob's callback ourselves to
// simulate the terminal reporting the outcome.
async function postPaymobCallback(obj, hmac = "test-signature") {
    // Every callback is authenticated by its hmac query arg (the test patches
    // _verify_hmac to accept it).
    const url = `/pos_paymob/notification?hmac=${hmac}`;
    const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ obj }),
    });
    if (!resp.ok) {
        throw new Error(`Paymob callback failed with status ${resp.status}`);
    }
}

// The controller reads it as "<session_id>_<payment_method_id>_<order_uuid>_<timestamp>".
function merchantOrderId(paymentMethodId, orderUuid) {
    const sessionId = posmodel.config.current_session_id.id;
    return `${sessionId}_${paymentMethodId}_${orderUuid}_0`;
}

export async function mockPaymobSaleCallback(transactionId = 7000001) {
    const line = posmodel.getPendingPaymentLine("paymob");
    await postPaymobCallback({
        id: transactionId,
        success: true,
        amount_cents: Math.round(line.amount * 100),
        order: {
            merchant_order_id: merchantOrderId(line.payment_method_id.id, line.pos_order_id.uuid),
        },
        source_data: { pan: "2345", sub_type: "MasterCard", type: "card" },
        data: { message: "Approved" },
    });
}

// A refund callback carries the ORIGINAL sale's uuid, captured onto the refund
// line by updateRefundPaymentLine.
export async function mockPaymobRefundCallback(transactionId = 7000001) {
    const line = posmodel.getPendingPaymentLine("paymob");
    await postPaymobCallback({
        id: transactionId,
        success: true,
        // A void re-sends the original sale transaction with the flag flipped, same id.
        is_voided: true,
        order: {
            merchant_order_id: merchantOrderId(
                line.payment_method_id.id,
                line.uiState.paymobRefundOrderUuid
            ),
        },
        source_data: { pan: "2345", sub_type: "MasterCard", type: "card" },
        data: { message: "Approved" },
    });
}
