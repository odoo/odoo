import { models } from "@web/../tests/web_test_helpers";

export class PosPaymentMethod extends models.ServerModel {
    _name = "pos.payment.method";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "payment_provider",
            "type",
            "image",
            "sequence",
            "payment_method_type",
            "default_qr",
        ];
    }

    _records = [
        {
            id: 2,
            name: "Card",
            payment_provider: false,
            type: "bank",
            image: false,
            sequence: 1,
            payment_method_type: "none",
            default_qr: false,
        },
        {
            id: 3,
            name: "Customer Account",
            payment_provider: false,
            type: "pay_later",
            image: false,
            sequence: 2,
            payment_method_type: "none",
            default_qr: false,
        },
        {
            id: 1,
            name: "Cash",
            payment_provider: false,
            type: "cash",
            image: false,
            sequence: 0,
            payment_method_type: "none",
            default_qr: false,
        },
    ];
}
