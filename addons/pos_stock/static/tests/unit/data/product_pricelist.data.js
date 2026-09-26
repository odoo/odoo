import { ProductPricelist } from "@point_of_sale/../tests/unit/data/product_pricelist.data";

ProductPricelist._records = [
    ...ProductPricelist._records,
    {
        id: 21,
        name: "Test Pricelist Price",
        display_name: "Test Pricelist Price (USD)",
        item_ids: [21, 22],
    },
];
