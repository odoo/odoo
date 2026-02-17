import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductTemplateAttributeValue extends Base {
    static pythonModel = "product.template.attribute.value";
    static enableLazyGetters = false;
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeValue.pythonModel, ProductTemplateAttributeValue);
