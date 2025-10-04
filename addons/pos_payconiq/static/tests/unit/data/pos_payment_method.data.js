import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";
import { ORM } from "@web/core/orm_service";
import { ErrorWithObjectBody } from "../utils/error";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "external_qr_sticker_size",
            "external_qr_usage",
            "payconiq_api_key",
            "payconiq_ppid",
        ];
    },
});

const create_payconiq_payment = ({ amount, paymentUuid }) => {
    if (amount <= 0) {
        throw new Error("Failed to create payment");
    }
    return Promise.resolve({
        uuid: paymentUuid,
        payconiq_id: "azertyuiop",
        qr_code: "https://example.com/qrcode/azertyuiop",
    });
};

const cancel_payconiq_payment = ({ payconiq_id }) => {
    if (payconiq_id === "failed") {
        const message = "Failed to cancel payment";
        throw new ErrorWithObjectBody(message, { message });
    }
    return Promise.resolve(true);
};

PosPaymentMethod._records.push(
    {
        id: 4,
        name: "Payconiq Display",
        external_qr_sticker_size: "S",
        external_qr_usage: "display",
        is_cash_count: false,
        is_online_payment: false,
        use_payment_terminal: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "display_api_key",
        payconiq_ppid: "display_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 3,
        default_qr: false,
    },
    {
        id: 5,
        name: "Payconiq Sticker 1",
        external_qr_sticker_size: "M",
        external_qr_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        use_payment_terminal: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "sticker_api_key",
        payconiq_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 4,
        default_qr: false,
    },
    {
        id: 6,
        name: "Payconiq Sticker 2",
        external_qr_sticker_size: "L",
        external_qr_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        use_payment_terminal: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "sticker_api_key",
        payconiq_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 5,
        default_qr: false,
    }
);

patch(ORM.prototype, {
    call(model, method, args = [], kwargs = {}) {
        if (model === "pos.payment.method") {
            // --- Create Payconiq Payment ---
            if (method === "create_payconiq_payment") {
                return create_payconiq_payment(kwargs);
            }

            // --- Cancel Payconiq Payment ---
            if (method === "cancel_payconiq_payment") {
                return cancel_payconiq_payment(kwargs);
            }
        }

        return super.call(model, method, args, kwargs);
    },
});
