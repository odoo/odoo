import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 15,
        product_tmpl_id: 15,
        lst_price: 0,
        standard_price: 0,
        display_name: "Down Payment (POS)",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
    },
];
