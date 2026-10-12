import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 200,
        name: "Gift Card Discount Product",
        display_name: "Gift Card Discount Product",
        type: "service",
        list_price: 0,
        standard_price: 0,
        uom_id: 1,
        available_in_pos: true,
        active: true,
        taxes_id: [],
        product_variant_ids: [200],
    },
];
