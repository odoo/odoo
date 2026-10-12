import { ProductPricelistItem } from "@point_of_sale/../tests/unit/data/product_pricelist_item.data";

ProductPricelistItem._records = [
    ...ProductPricelistItem._records,
    {
        id: 101,
        fixed_price: 15.0,
        compute_price: "fixed",
        pricelist_id: 101,
        product_tmpl_id: 101,
        product_id: 101,
    },
    {
        id: 102,
        fixed_price: 20.0,
        compute_price: "fixed",
        pricelist_id: 101,
        product_tmpl_id: 101,
        product_id: 102,
    },
];
