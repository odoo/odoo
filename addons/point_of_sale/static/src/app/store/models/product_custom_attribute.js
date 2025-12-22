import { Reactive } from "@web/core/utils/reactive";

export class ProductCustomAttribute extends Reactive {
    constructor() {
        super();
        this.setup(...arguments);
    }

    setup({ id, name, custom_value, custom_product_template_attribute_value_id }) {
        this.id = id;
        this.name = name;
        this.custom_value = custom_value;
        this.custom_product_template_attribute_value_id =
            custom_product_template_attribute_value_id;
    }

    get value() {
        return this.custom_value;
    }
}
