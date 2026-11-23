/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Product extends Reactive {
    constructor(
        {
            price_info,
            has_image,
            attributes,
            name,
            id,
            description_self_order,
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
        this.description_self_order = product.description_self_order;
        this.pos_categ_ids = product.pos_categ_ids;
        this.pos_combo_ids = product.pos_combo_ids;
        this.is_pos_groupable = product.is_pos_groupable;
        this.write_date = product.write_date;
        this.self_order_available = product.self_order_available;
        this.barcode = product.barcode;

        // data
        this.showPriceTaxIncluded = showPriceTaxIncluded;
    }

    get isCombo() {
        return this.pos_combo_ids;
    }
}
