import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "bancontact_usage"];
    },

    _get_payment_provider_names() {
        return { ...super._get_payment_provider_names(), bancontact_pay: "Bancontact Pay" };
    },
});

PosPaymentMethod._records.push(
    {
        id: 4,
        name: "Bancontact Display",
        bancontact_usage: "display",
        payment_provider: "bancontact_pay",
        payment_method_type: "qr",
        type: "bank",
        image: false,
        sequence: 3,
        config_ids: [1],
    },
    {
        id: 5,
        name: "Bancontact Sticker 1",
        bancontact_usage: "sticker",
        payment_provider: "bancontact_pay",
        payment_method_type: "qr",
        type: "bank",
        image: false,
        sequence: 4,
        config_ids: [1],
    },
    {
        id: 6,
        name: "Bancontact Sticker 2",
        bancontact_usage: "sticker",
        payment_provider: "bancontact_pay",
        payment_method_type: "qr",
        type: "bank",
        image: false,
        sequence: 5,
        config_ids: [1],
    }
);
