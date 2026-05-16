import { ProductPricelist } from "@point_of_sale/../tests/unit/data/product_pricelist.data";

ProductPricelist._records = [
    ...ProductPricelist._records,
    {
        id: 4,
        name: "Test Pricelist Variants",
        display_name: "Test Pricelist Variants (USD)",
        item_ids: [3, 4],
    },
];
