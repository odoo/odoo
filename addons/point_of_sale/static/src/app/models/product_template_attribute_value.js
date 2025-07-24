import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductTemplateAttributeValue extends Base {
    static pythonModel = "product.template.attribute.value";

    get exclusions() {
        const values = this.models["product.template.attribute.value"].filter((value) =>
            value.excluded_value_ids.some(({ id })=> id === this.id)
        );

        return [...this.excluded_value_ids, ...values];
    }

    doHaveConflictWith(values) {
        const excludedIds = values.map(({ id }) => id);
        return this.exclusions.some(({ id }) => excludedIds.includes(id));
    }
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeValue.pythonModel, ProductTemplateAttributeValue);
