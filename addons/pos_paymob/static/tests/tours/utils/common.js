/* global posmodel */

// No terminal in a tour: post Paymob's callback ourselves.
async function postPaymobCallback(obj, hmac = "test-signature") {
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

function merchantOrderId(paymentMethodId, orderUuid) {
    const sessionId = posmodel.config.current_session_id.id;
    return `${sessionId}_${paymentMethodId}_${orderUuid}_0`;
}

export async function mockPaymobSaleCallback(transactionId = 7000001) {
    // Not getPendingPaymentLine: it skips a cancelled line the customer may still pay.
    const line = posmodel.getOrder().getSelectedPaymentline();
    await postPaymobCallback({
        id: transactionId,
        success: true,
        amount_cents: Math.round(line.amount * 100),
        order: {
            id: Number(line.uiState.paymobOrderId),
            merchant_order_id: merchantOrderId(line.payment_method_id.id, line.pos_order_id.uuid),
        },
        source_data: { pan: "2345", sub_type: "MasterCard", type: "card" },
        data: { message: "Approved" },
    });
}

// A refund callback re-sends the original sale transaction.
export async function mockPaymobRefundCallback() {
    const line = posmodel.getPendingPaymentLine("paymob");
    await postPaymobCallback({
        id: Number(line.uiState.paymobRefundTransactionId),
        success: true,
        is_voided: true,
        order: {
            merchant_order_id: merchantOrderId(line.payment_method_id.id, line.pos_order_id.uuid),
        },
        source_data: { pan: "2345", sub_type: "MasterCard", type: "card" },
        data: { message: "Approved" },
    });
}
