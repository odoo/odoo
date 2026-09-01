import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { attributeCacheVersion } from "./product_template";

export class ProductTemplateAttributeValue extends Base {
    static pythonModel = "product.template.attribute.value";
    static enableLazyGetters = false;

    setup(_vals) {
        super.setup(_vals);
        attributeCacheVersion.value++; // To invalidate the searchString of the templates
    }
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeValue.pythonModel, ProductTemplateAttributeValue);
