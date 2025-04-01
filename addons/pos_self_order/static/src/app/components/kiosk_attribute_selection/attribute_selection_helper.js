export class AttributeSelectionHelper {
    constructor() {
        this.selectedValues = {};
    }

    getSelectedValues(attribute) {
        return (this.selectedValues[attribute.id] ??= new Set());
    }

    isValueSelected(attribute, value) {
        return this.getSelectedValues(attribute).has(value.id);
    }

    hasValueSelected(attribute) {
        return this.getSelectedValues(attribute).size > 0;
    }

    selectAttribute(attribute, value, onSelection = () => {}) {
        const isMultiSelection = attribute.attribute_id.display_type === "multi";
        const values = this.getSelectedValues(attribute);
        if (values.has(value.id)) {
            values.delete(value.id);
        } else {
            if (!isMultiSelection) {
                values.clear();
            }
            values.add(value.id);
            onSelection(!isMultiSelection, value);
        }
    }

    hasMissingAttributeValues(attributes) {
        return attributes.some(
            (attr) => attr.attribute_id.display_type !== "multi" && !this.hasValueSelected(attr)
        );
    }

    getAllSelectedAttributeValuesIds() {
        return Object.values(this.selectedValues).flatMap((value) => [...value]);
    }

    getSelectedAttributeValues(attribute) {
        return attribute.product_template_value_ids.filter((value) =>
            this.isValueSelected(attribute, value)
        );
    }
}
