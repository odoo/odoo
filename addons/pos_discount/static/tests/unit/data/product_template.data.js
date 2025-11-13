import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

ProductTemplate._records = [
    ...ProductTemplate._records,
    {
        id: 151,
        name: "Discount",
        display_name: "Discount",
        list_price: 0,
        standard_price: 0,
        type: "consu",
        service_tracking: "none",
        pos_categ_ids: [1],
        categ_id: false,
        uom_id: 1,
        available_in_pos: true,
        active: true,
    },
];
