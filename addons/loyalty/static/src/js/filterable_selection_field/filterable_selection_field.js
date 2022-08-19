/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";

export class FilterableSelectionField extends SelectionField {
    /**
     * @override
     */
    get options() {
        let options = super.options;
        if (this.props.allowed_selection_values) {
            options = options.filter((option) => {
                return option[0] === this.props.value || this.props.allowed_selection_values.includes(option[0])
            });
        }
        return options;
    }
};

FilterableSelectionField.props = {
    ...SelectionField.props,
    allowed_selection_values: { type: Array, optional: true },
};

FilterableSelectionField.extractProps = ({ attrs }) => {
    return {
        ...SelectionField.extractProps({ attrs }),
        allowed_selection_values: attrs.options.allowed_selection_values,
    };
};

registry.category("fields").add("filterable_selection", FilterableSelectionField);