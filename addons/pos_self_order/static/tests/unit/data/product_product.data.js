import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "self_order_available"];
    },
});

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 19,
        product_tmpl_id: 19,
        lst_price: 10,
        standard_price: 0,
        display_name: "T-Shirt (S)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [1],
    },
    {
        id: 20,
        product_tmpl_id: 19,
        lst_price: 15,
        standard_price: 0,
        display_name: "T-Shirt (M)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [2],
    },
].map((record) => ({
    ...record,
    self_order_available: true,
}));
