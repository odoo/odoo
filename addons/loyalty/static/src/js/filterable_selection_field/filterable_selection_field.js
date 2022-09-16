/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";

/**
 * The purpose of this field is to be able to define some values which should not be
 * displayed on our selection field, this way we can have multiple views for the same model
 * that uses different possible sets of values on the same selection field.
 */
export class FilterableSelectionField extends SelectionField {
    /**
     * @override
     */
    get options() {
        let options = super.options;
        if (this.props.whitelisted_values) {
            options = options.filter((option) => {
                return option[0] === this.props.value || this.props.whitelisted_values.includes(option[0])
            });
        } else if (this.props.blacklisted_values) {
            options = options.filter((option) => {
                return option[0] === this.props.value || !this.props.blacklisted_values.includes(option[0]);
            });
        }
        return options;
    }
};

FilterableSelectionField.props = {
    ...SelectionField.props,
    whitelisted_values: { type: Array, optional: true },
    blacklisted_values: { type: Array, optional: true },
};

FilterableSelectionField.extractProps = ({ attrs }) => {
    return {
        ...SelectionField.extractProps({ attrs }),
        whitelisted_values: attrs.options.whitelisted_values,
        blacklisted_values: attrs.options.blacklisted_values,
    };
};

registry.category("fields").add("filterable_selection", FilterableSelectionField);
