import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "bancontact_usage"];
    },

    create_bancontact_payment(id, ...args) {
        const { amount, payment_id } = args[0];
        if (amount <= 0) {
            throw new Error("Failed to create payment");
        }
        const PosPayment = this.env["pos.payment"];
        const pos_payment_id = PosPayment.search([["id", "=", payment_id]])[0];
        const pos_payment = PosPayment.read(
            [pos_payment_id],
            PosPayment._load_pos_data_fields(),
            false
        )[0];
        pos_payment.bancontact_id = "bancontact_" + pos_payment_id;
        pos_payment.qr_code = "https://example.com/qrcode/bancontact_" + pos_payment_id;

        return {
            "pos.payment": [pos_payment],
        };
    },

    cancel_bancontact_payment(id, ...args) {
        const { payment_id, force_cancel } = args[0];
        const PosPayment = this.env["pos.payment"];
        const pos_payment_id = PosPayment.search([["id", "=", payment_id]])[0];
        const pos_payment = PosPayment.read(
            [pos_payment_id],
            PosPayment._load_pos_data_fields(),
            false
        )[0];

        if (!force_cancel && pos_payment.amount < 0) {
            throw new Error(`Failed to cancel payment (ERR: ${-pos_payment.amount})`);
        }
        pos_payment.bancontact_id = null;
        pos_payment.qr_code = null;

        return {
            "pos.payment": [pos_payment],
        };
    },
});

PosPaymentMethod._records.push(
    {
        id: 4,
        name: "Bancontact Display",
        bancontact_sticker_size: "S",
        bancontact_usage: "display",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "bancontact_pay",
        payment_method_type: "external_qr",
        bancontact_api_key: "display_api_key",
        bancontact_ppid: "display_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 3,
        default_qr: false,
    },
    {
        id: 5,
        name: "Bancontact Sticker 1",
        bancontact_sticker_size: "M",
        bancontact_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "bancontact_pay",
        payment_method_type: "external_qr",
        bancontact_api_key: "sticker_api_key",
        bancontact_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 4,
        default_qr: false,
    },
    {
        id: 6,
        name: "Bancontact Sticker 2",
        bancontact_sticker_size: "L",
        bancontact_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "bancontact_pay",
        payment_method_type: "external_qr",
        bancontact_api_key: "sticker_api_key",
        bancontact_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 5,
        default_qr: false,
    }
);
