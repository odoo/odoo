import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "all_product_tag_ids"];
    },
});
