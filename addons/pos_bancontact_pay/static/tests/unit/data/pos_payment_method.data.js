import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "bancontact_usage"];
    },

    create_bancontact_payment(id, data) {
        if (this[id].payment_provider !== "bancontact_pay") {
            throw new Error("Error Server: Wrong Provider");
        }

        if (data.amount < 0) {
            throw new Error(`Failed to create payment (ERR: ${-data.amount})`);
        }

        return {
            bancontact_id: "bancontact_id",
            qr_code: "bancontact_qr_code",
        };
    },

    cancel_bancontact_payment(id, bancontact_id) {
        if (this[id].payment_provider !== "bancontact_pay") {
            throw new Error("Error Server: Wrong Provider");
        }

        if (typeof bancontact_id === "number" && bancontact_id < 0) {
            throw new Error(`Failed to cancel payment (ERR: ${-bancontact_id})`);
        }
    },
});

PosPaymentMethod._records.push(
    {
        id: 4,
        name: "Bancontact Display",
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
        config_ids: [1],
    },
    {
        id: 5,
        name: "Bancontact Sticker 1",
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
        config_ids: [1],
    },
    {
        id: 6,
        name: "Bancontact Sticker 2",
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
        config_ids: [1],
    }
);
