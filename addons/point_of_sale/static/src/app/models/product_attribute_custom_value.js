import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductAttributeCustomValue extends Base {
    static pythonModel = "product.attribute.custom.value";

    get order_id() {
        return this.pos_order_line_id?.order_id;
    }
}

registry
    .category("pos_available_models")
    .add(ProductAttributeCustomValue.pythonModel, ProductAttributeCustomValue);
