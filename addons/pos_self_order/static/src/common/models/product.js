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
            description_sale,
            pos_categ_ids,
            is_pos_groupable,
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
        this.description_sale = product.description_sale;
        this.pos_categ_ids = product.pos_categ_ids;
        this.is_pos_groupable = product.is_pos_groupable;

        // data
        this.showPriceTaxIncluded = showPriceTaxIncluded;
    }

    get prices() {
        return this.showPriceTaxIncluded
            ? this.price_info.price_with_tax
            : this.price_info.price_without_tax;
    }
}
