import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductTemplateAttributeValue extends Base {
    static pythonModel = "product.template.attribute.value";
<<<<<<< d0f75f1c4edec9905e9657d73e5eebf15765bfa6

    get exclusions() {
        const values = this.models["product.template.attribute.value"].filter((value) =>
            value.exclude_for.some(({ value_ids }) => value_ids.some(({ id }) => id === this.id))
        );

        return [...this.exclude_for.flatMap(({ value_ids }) => value_ids), ...values];
    }

    doHaveConflictWith(values) {
        const excludedIds = values.map(({ id }) => id);
        return this.exclusions.some(({ id }) => excludedIds.includes(id));
    }
||||||| 216773812903f039e47ebaa8e606aac7c23361c2

    setup() {
        super.setup(...arguments);
    }

    get exclusions() {
        const values = this.models["product.template.attribute.value"].filter((value) =>
            value.exclude_for.some(({ value_ids }) => value_ids.some(({ id }) => id === this.id))
        );

        return [...this.exclude_for.flatMap(({ value_ids }) => value_ids), ...values];
    }

    doHaveConflictWith(values) {
        const excludedIds = values.map(({ id }) => id);
        return this.exclusions.some(({ id }) => excludedIds.includes(id));
    }
=======
>>>>>>> a3b5ddd909ceb3b09acd0ebb1dde6f2561a8244e
}

registry
    .category("pos_available_models")
    .add(ProductTemplateAttributeValue.pythonModel, ProductTemplateAttributeValue);
