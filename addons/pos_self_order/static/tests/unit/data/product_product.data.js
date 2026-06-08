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
        id: 101,
        product_tmpl_id: 101,
        lst_price: 10,
        standard_price: 0,
        display_name: "T-Shirt (S)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [101],
    },
    {
        id: 102,
        product_tmpl_id: 101,
        lst_price: 15,
        standard_price: 0,
        display_name: "T-Shirt (M)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [102],
    },
    {
        id: 103,
        product_tmpl_id: 102,
        lst_price: 200,
        standard_price: 0,
        display_name: "Smart Watch",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
    },
    {
        id: 104,
        product_tmpl_id: 103,
        lst_price: 100,
        standard_price: 0,
        display_name: "Running Sweater (S)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [101],
    },
    {
        id: 105,
        product_tmpl_id: 103,
        lst_price: 105,
        standard_price: 0,
        display_name: "Running Sweater (M)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [102],
    },
].map((record) => ({
    ...record,
    self_order_available: true,
}));
