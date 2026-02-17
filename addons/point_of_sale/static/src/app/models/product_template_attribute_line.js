import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductTemplateAttributeLine extends Base {
    static pythonModel = "product.template.attribute.line";
    static enableLazyGetters = false;
    values() {
        return this.product_template_value_ids;
    }
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeLine.pythonModel, ProductTemplateAttributeLine);
