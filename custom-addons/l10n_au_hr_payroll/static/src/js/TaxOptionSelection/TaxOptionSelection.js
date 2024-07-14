/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

/**
 * The purpose of this field is to restrict the options available in the selection field
 * based on the value of the tax category field, as defined by the ATO.
 */
export class TaxOptionSelectionField extends SelectionField {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.taxCategoryValuesMap = {
            "R": ["T", "N", "D"],
            "A": ["T", "N", "D", "P"],
            "C": ["T", "F"],
            "S": ["S", "M", "I"],
            "H": ["R", "U", "F"],
            "W": ["P"],
            "F": ["F"],
            "N": ["F", "A"],
            "D": ["V", "B", "Z"],
            "V": ["C", "O"],
        };
    }
    /**
     * @override
     */
    get options() {
        let options = super.options;
        const values = this.taxCategoryValuesMap[this.props.record.data.l10n_au_tax_treatment_category];
        options = options.filter((option) => values.includes(option[0]));
        return options;
    }
    /**
     * @override
     */
    get value() {
        let value = super.value;
        const selection = this.taxCategoryValuesMap[this.props.record.data.l10n_au_tax_treatment_category];
        if (value && !selection.includes(value)) {
            this.props.record.update({[this.props.name]: selection[0]});
            return selection[0]
        }
        return value;
    }
};

TaxOptionSelectionField.props = {
    ...SelectionField.props,
};

export const taxOptionSelectionField = {
    ...selectionField,
    component: TaxOptionSelectionField,
    fieldDependencies: [{ name: "l10n_au_tax_treatment_category", type: "selection" }],
};

registry.category("fields").add("l10n_au_tax_selection", taxOptionSelectionField);
