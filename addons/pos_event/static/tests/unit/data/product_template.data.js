import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 108,
        name: "Event Registration",
        display_name: "Event Registration",
        list_price: 30.0,
        standard_price: 30.0,
        type: "service",
        service_tracking: "event",
        pos_categ_ids: [1],
        categ_id: false,
        uom_id: 1,
        available_in_pos: true,
        active: true,
    },
];
