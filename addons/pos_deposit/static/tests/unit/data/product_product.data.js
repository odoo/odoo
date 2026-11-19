import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

patch(ProductProduct.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "deposit_product_id"];
    },
});

ProductProduct._records = [
    ...ProductProduct._records.map((record) =>
        [5, 7, 8].includes(record.id) ? { ...record, deposit_product_id: 9100 } : record
    ),
    {
        ...ProductProduct._records.find((record) => record.id === 5),
        id: 9100,
        product_tmpl_id: 9100,
        display_name: "Deposit",
        lst_price: 1,
        barcode: false,
    },
];
