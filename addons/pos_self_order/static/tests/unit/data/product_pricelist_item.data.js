import { ProductPricelistItem } from "@point_of_sale/../tests/unit/data/product_pricelist_item.data";

ProductPricelistItem._records = [
    ...ProductPricelistItem._records,
    {
        id: 3,
        fixed_price: 15.0,
        compute_price: "fixed",
        pricelist_id: 4,
        product_tmpl_id: 19,
        product_id: 19,
    },
    {
        id: 4,
        fixed_price: 20.0,
        compute_price: "fixed",
        pricelist_id: 4,
        product_tmpl_id: 19,
        product_id: 20,
    },
];
