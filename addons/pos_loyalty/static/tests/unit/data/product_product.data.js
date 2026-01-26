import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "all_product_tag_ids"];
    },
});

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 200,
        name: "Gift Card Discount Product",
        product_tmpl_id: 200,
        lst_price: 0,
        standard_price: 0,
        display_name: "Gift Card Discount Product",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        pos_categ_ids: [],
        all_product_tag_ids: [],
    },
];
