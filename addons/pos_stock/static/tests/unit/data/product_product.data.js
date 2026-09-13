import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 41,
        product_tmpl_id: 41,
        lst_price: 10,
        standard_price: 0,
        display_name: "Screw",
        product_tag_ids: [],
        barcode: false,
    },
];
