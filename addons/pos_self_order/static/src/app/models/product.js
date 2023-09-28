/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { markup } from "@odoo/owl";

export class Product extends Reactive {
    constructor(
        {
            price_info,
            has_image,
            attributes,
            name,
            id,
            description_ecommerce,
            pos_categ_ids,
            pos_combo_ids,
            is_pos_groupable,
            write_date,
            self_order_available,
        },
        showPriceTaxIncluded
    ) {
        super();
        this.setup(...arguments);
    }

    setup(product, showPriceTaxIncluded) {
        // server data
        this.id = product.id;
        this.price_info = product.price_info;
        this.has_image = product.has_image;
        this.attributes = product.attributes;
        this.name = product.name;
        this.description_ecommerce = product.description_ecommerce
            ? markup(product.description_ecommerce)
            : false;
        this.pos_categ_ids = product.pos_categ_ids;
        this.pos_combo_ids = product.pos_combo_ids;
        this.is_pos_groupable = product.is_pos_groupable;
        this.write_date = product.write_date;
        this.self_order_available = product.self_order_available;

        // data
        this.showPriceTaxIncluded = showPriceTaxIncluded;
    }

    get prices() {
        return this.price_info.display_price;
    }

    get isCombo() {
        return this.pos_combo_ids;
    }
}
