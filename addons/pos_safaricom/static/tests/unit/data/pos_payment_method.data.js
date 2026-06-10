import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "safaricom_payment_type"];
    },

    mpesa_express_send_payment_request(ids, data) {
        return {
            success: false,
            checkout_request_id: data.checkout_request_id,
            merchant_request_id: "TEST-MR-123",
            message: "Request accepted for processing",
        };
    },

    generate_qr_code() {
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB";
    },

    mark_transaction_used() {
        return true;
    },
});

PosPaymentMethod._records.push(
    {
        id: 7,
        name: "M-PESA Express",
        is_cash_count: false,
        payment_provider: "safaricom",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 3,
        payment_method_type: "none",
        default_qr: false,
        safaricom_payment_type: "mpesa_express",
    },
    {
        id: 8,
        name: "Lipa na M-PESA",
        is_cash_count: false,
        payment_provider: "safaricom",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 4,
        payment_method_type: "none",
        default_qr: false,
        safaricom_payment_type: "lipa_na_mpesa",
    }
);
