import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 301,
        name: "Gift Card Discount Product",
        display_name: "Gift Card Discount Product",
        list_price: 0,
        standard_price: 0,
        taxes_id: [4],
        type: "service",
        service_tracking: "no",
        categ_id: false,
        pos_categ_ids: [],
        uom_id: 1,
        available_in_pos: true,
        active: true,
        product_variant_ids: [301],
    },
];
