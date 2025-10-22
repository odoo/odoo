export class AttributeSelectionHelper {
    constructor(selfOrder) {
        this.selectedValues = {};
        this.customValues = {};
        this.selfOrder = selfOrder;
    }

    getCustomValue(attribute, value) {
        if (!value.is_custom || attribute.display_type === "multi") {
            return null;
        }
        this.customValues[attribute.id] ??= {};
        return (this.customValues[attribute.id][value.id] ??= {
            custom_product_template_attribute_value_id: value.id,
            custom_value: "",
        });
    }

    getAllCustomValues() {
        return Object.fromEntries(
            Object.values(this.customValues).flatMap((value) => Object.entries(value))
        );
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

    getSelectedValue(attribute) {
        return this.getSelectedValues(attribute).values().next().value;
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
            onSelection(!isMultiSelection, attribute, value);
        }
    }

    getMissingAttributeValue(attributes) {
        return attributes.find(
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
