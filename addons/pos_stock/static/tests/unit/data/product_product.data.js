import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "tracking"];
    },
});

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 26,
        product_tmpl_id: 26,
        lst_price: 100,
        standard_price: 0,
        display_name: "Lot Tracked Product",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
    },
    {
        id: 27,
        product_tmpl_id: 27,
        lst_price: 100,
        standard_price: 0,
        display_name: "Serial Tracked Product",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
    },
].map((record) => ({
    ...record,
    tracking: record.tracking ?? "none",
}));
