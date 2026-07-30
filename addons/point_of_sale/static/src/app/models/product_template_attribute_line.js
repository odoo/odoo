import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { attributeCacheVersion } from "./product_template";

export class ProductTemplateAttributeLine extends Base {
    static pythonModel = "product.template.attribute.line";
    static enableLazyGetters = false;

    setup(_vals) {
        super.setup(_vals);
        attributeCacheVersion.value++; // To invalidate the searchString of the templates
    }

    values() {
        return this.product_template_value_ids;
    }
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeLine.pythonModel, ProductTemplateAttributeLine);
