/* global posmodel */

const response_from_qfpay_on_pos_payment_webhook = (uuid, sessionID, paymentMethodId, amount) => ({
    cash_fee_type: "",
    exchange_rate: "",
    cancel: "0",
    pay_type: "802808",
    txdtm: "2025-08-26 17:50:34",
    out_trade_no: `${uuid}--${sessionID}--${paymentMethodId}`,
    syssn: "20250826155400087645770447",
    status: "1",
    sysdtm: "2025-08-26 17:50:36",
    paydtm: "2025-08-26 17:50:37",
    goods_name: "",
    txcurrcd: "HKD",
    mchid: "8Bx9aHgNmaQJ",
    customer_source: "HK",
    cash_fee: "0",
    chnlsn2: "",
    cardcd: "",
    txamt: `${amount}`,
    outcardnm: "",
    respcd: "0000",
    goods_info: "",
    notify_type: "payment",
    chnlsn: "2025085675626675",
});

const response_from_qfpay_on_pos_refund_webhook = (uuid, sessionID, paymentMethodId, amount) => ({
    status: "1",
    sysdtm: "2025-08-26 17:51:34",
    txcurrcd: "HKD",
    orig_out_trade_no: `${uuid}--${sessionID}--${paymentMethodId}`,
    mchid: "8Bx9jdHgmaQJ",
    txdtm: "2025-08-26 17:51:34",
    txamt: `${amount}`,
    orig_syssn: "20250826155400087645770447",
    out_trade_no: "2cccf6c02d4835bdb79d7c96beb95cbf",
    syssn: "20250821155400847635342115",
    respcd: "0000",
    notify_type: "cancel",
});

// Once request for payment/refund has been sent to the qfpay terminal
// we wait to receive the notification from qfpay on the webhook
// The simplest way to mock this notification is to send it ourselves.
export async function mockQFPayWebhook(uuid, paymentMethodId, amount, isRefund = false) {
    const sessionId = posmodel.config.current_session_id.id;
    const resp = await fetch("/qfpay/notify", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(
            isRefund
                ? response_from_qfpay_on_pos_refund_webhook(
                      uuid,
                      sessionId,
                      paymentMethodId,
                      Math.trunc(amount * 100)
                  )
                : response_from_qfpay_on_pos_payment_webhook(
                      uuid,
                      sessionId,
                      paymentMethodId,
                      Math.trunc(amount * 100)
                  )
        ),
    });
    if (!resp.ok) {
        throw new Error("Failed to notify Qfpay webhook");
    }
}
