import { ProductPricelistItem } from "@point_of_sale/../tests/unit/data/product_pricelist_item.data";

ProductPricelistItem._records = [
    ...ProductPricelistItem._records,
    {
        id: 21,
        fixed_price: 20.0,
        compute_price: "fixed",
        min_quantity: 2,
        pricelist_id: 21,
        product_tmpl_id: 41,
    },
    {
        id: 22,
        fixed_price: 30.0,
        min_quantity: 1,
        compute_price: "fixed",
        pricelist_id: 21,
        product_tmpl_id: 41,
    },
];
