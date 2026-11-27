import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "is_deposit"];
    },
});

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        ...ProductTemplate._records.find((record) => record.id === 5),
        id: 9100,
        display_name: "Deposit",
        name: "Deposit",
        list_price: 1,
        taxes_id: [],
        is_favorite: false,
        is_deposit: true,
        product_variant_ids: [9100],
    },
];
