import { models } from "@web/../tests/web_test_helpers";

export class ProductPricelistItem extends models.ServerModel {
    _name = "product.pricelist.item";

    _load_pos_data_fields() {
        return [
            "product_tmpl_id",
            "product_id",
            "pricelist_id",
            "price_surcharge",
            "price_discount",
            "price_round",
            "price_min_margin",
            "price_max_margin",
            "company_id",
            "currency_id",
            "date_start",
            "date_end",
            "compute_price",
            "fixed_price",
            "percent_price",
            "base_pricelist_id",
            "base",
            "categ_id",
            "min_quantity",
        ];
    }

    _records = [
        {
            id: 1,
            product_tmpl_id: false,
            product_id: false,
            pricelist_id: 1,
            price_surcharge: 0.0,
            price_discount: 0.0,
            price_round: 0.0,
            price_min_margin: 0.0,
            price_max_margin: 0.0,
            company_id: 250,
            currency_id: 1,
            date_start: false,
            date_end: false,
            compute_price: "fixed",
            fixed_price: 3.0,
            percent_price: 0.0,
            base_pricelist_id: false,
            base: "list_price",
            categ_id: false,
            min_quantity: 0.0,
        },
        {
            id: 2,
            base: "list_price",
            company_id: 250,
            compute_price: "percentage",
            currency_id: 1,
            pricelist_id: 3,
            percent_price: 90.0,
        },
    ];
}
