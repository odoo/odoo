import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "sale_line_warn_msg", "invoice_policy"];
    },
});

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 105,
        display_name: "Down Payment (POS)",
        standard_price: 0,
        categ_id: false,
        pos_categ_ids: [],
        taxes_id: [],
        barcode: false,
        name: "Down Payment (POS)",
        list_price: 0,
        is_favorite: false,
        default_code: false,
        to_weight: false,
        uom_id: 1,
        description_sale: false,
        description: false,
        tracking: "none",
        type: "service",
        service_tracking: "no",
        is_storable: false,
        write_date: "2025-07-03 17:04:14",
        color: 0,
        pos_sequence: 5,
        available_in_pos: true,
        attribute_line_ids: [],
        active: true,
        image_128: false,
        sequence: 1,
        combo_ids: [],
        product_variant_ids: [7],
        public_description: false,
        pos_optional_product_ids: [],
        product_tag_ids: [],
    },
];
