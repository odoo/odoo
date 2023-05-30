/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Product extends Reactive {
    constructor(
        {
            price_info,
            has_image,
            attributes,
            name,
            product_id,
            description_sale,
            tags,
            is_pos_groupable,
        },
        selfOrder
    ) {
        super();
        this.setup(...arguments);
    }

    setup(product, selfOrder) {
        // server data
        this.id = product.product_id;
        this.price_info = product.price_info;
        this.has_image = product.has_image;
        this.attributes = product.attributes;
        this.name = product.name;
        this.description_sale = product.description_sale;
        this.tags = product.tags;
        this.is_pos_groupable = product.is_pos_groupable;

        // data
        this.selfOrder = selfOrder;
    }

    get prices() {
        return this.selfOrder.show_prices_with_tax_included
            ? this.price_info.price_with_tax
            : this.price_info.price_without_tax;
    }
}
