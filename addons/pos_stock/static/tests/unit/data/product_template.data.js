import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "tracking"];
    },
});

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 41,
        display_name: "Screw",
        standard_price: 0,
        categ_id: false,
        pos_categ_ids: [],
        taxes_id: [],
        barcode: false,
        name: "Screw",
        list_price: 10,
        is_favorite: false,
        default_code: false,
        to_weight: false,
        uom_id: 1,
        description_sale: false,
        description: false,
        type: "consu",
        tracking: "lot",
        service_tracking: "no",
        is_storable: true,
        write_date: "2026-07-03 13:04:14",
        color: 0,
        pos_sequence: 5,
        available_in_pos: true,
        attribute_line_ids: [],
        active: true,
        image_128: false,
        product_variant_ids: [41],
        public_description: false,
        pos_optional_product_ids: [],
        sequence: 1,
        product_tag_ids: [],
    },
];
