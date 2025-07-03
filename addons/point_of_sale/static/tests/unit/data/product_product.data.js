import { models } from "@web/../tests/web_test_helpers";

export class ProductProduct extends models.ServerModel {
    _name = "product.product";

    // NOTE - We don't take into account _eval_taxes_computation_prepare_product_fields
    _load_pos_data_fields() {
        return [
            "id",
            "lst_price",
            "display_name",
            "product_tmpl_id",
            "product_template_variant_value_ids",
            "product_template_attribute_value_ids",
            "barcode",
            "product_tag_ids",
            "default_code",
            "standard_price",
        ];
    }

    _records = [
        {
            id: 1,
            product_tmpl_id: 1,
            lst_price: 1,
            standard_price: 0,
            display_name: "TIP",
            product_tag_ids: [],
            barcode: false,
            default_code: false,
            product_template_attribute_value_ids: [],
            product_template_variant_value_ids: [],
        },
        {
            id: 5,
            product_tmpl_id: 5,
            lst_price: 100,
            standard_price: 0,
            display_name: "TEST",
            product_tag_ids: [],
            barcode: "test_test",
            default_code: false,
            product_template_attribute_value_ids: [],
            product_template_variant_value_ids: [],
        },
        {
            id: 6,
            product_tmpl_id: 6,
            lst_price: 100,
            standard_price: 0,
            display_name: "TEST 2",
            product_tag_ids: [],
            barcode: false,
            default_code: false,
            product_template_attribute_value_ids: [],
            product_template_variant_value_ids: [],
        },
    ];
}
