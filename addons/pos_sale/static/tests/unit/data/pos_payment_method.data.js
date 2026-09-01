import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "use_sale_order_payment"];
    },
});

PosPaymentMethod._records = [
    ...PosPaymentMethod._records,
    {
        id: 21,
        name: "Online Paid SO Payment",
        payment_provider: false,
        type: "pay_later",
        image: false,
        sequence: 21,
        use_sale_order_payment: true,
        payment_method_type: "none",
        default_qr: false,
    },
];
