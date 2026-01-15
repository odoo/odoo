import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "self_order_available"];
    },
});

ProductTemplate._records = ProductTemplate._records.map((record) => ({
    ...record,
    self_order_available: true,
}));
