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
            "currency_ids",
        ];
    }

    // Labels of the `payment_provider` selection, extended by the provider modules
    _get_payment_provider_names() {
        return {};
    }

    _load_pos_data_read(records) {
        const names = this._get_payment_provider_names();
        for (const record of records) {
            record._payment_provider_name = names[record.payment_provider] || false;
        }
        return records;
    }

    get_qr_code_value(
        _amount,
        _free_communication,
        _structured_communication,
        _currency,
        _debtor_partner
    ) {
        return "http://localhost:4444";
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
            currency_ids: [1],
            write_date: "2025-01-01 10:00:00",
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
            currency_ids: [],
            write_date: "2025-01-01 10:00:00",
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
            currency_ids: [125],
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
