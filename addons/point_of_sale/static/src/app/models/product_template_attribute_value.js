import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductTemplateAttributeValue extends Base {
    static pythonModel = "product.template.attribute.value";

    doHaveConflictWith(values) {
        if (
            this.exclude_for.some(({ value_ids }) =>
                value_ids.some((v) => values.some((value) => value.id === v.id))
            )
        ) {
            return true;
        }
        for (const value of values) {
            const exclusion = this.models["product.template.attribute.exclusion"].getBy(
                "product_template_attribute_value_id",
                value.id
            );
            if (exclusion?.value_ids.some((v) => v.id === this.id)) {
                return true;
            }
        }
        return false;
    }
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeValue.pythonModel, ProductTemplateAttributeValue);
