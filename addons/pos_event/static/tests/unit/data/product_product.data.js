import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 106,
        name: "Event Registration",
        display_name: "Event Registration",
        lst_price: 30.0,
        standard_price: 30.0,
        type: "service",
        service_tracking: "event",
        product_tmpl_id: 108,
    },
];
