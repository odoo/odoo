import { registry } from "@web/core/registry";
import { SelectionField, selectionField  } from "@web/views/fields/selection/selection_field";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { useState } from "@odoo/owl";

export class DynamicSelectionField extends SelectionField {
    static props = {
        ...SelectionField.props,
        canExcludeOptions: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({ excludedOptions: new Set() });

        useRecordObserver(async (record) => {
            this.props.canExcludeOptions.forEach(field => {
                field.exclude_options_for_values.forEach(exclusion => {
                    if (record.data[field.field] && exclusion.values.includes(record.data[field.field])) {
                        exclusion.options.forEach(this.state.excludedOptions.add,this.state.excludedOptions);
                    }
                });
            });
        });
    }

    /**
     * @override
     */
    get options() {
        let options = super.options;
        options = options.filter((option) => {
            return (
                option[0] === this.props.record.data[this.props.name] ||
                !this.state.excludedOptions.has(option[0])
            );
        });
        return options;
    };
}

export const dynamicSelectionField = {
    ...selectionField,
    component: DynamicSelectionField,
    supportedOptions: [
        {
            label: "Can Exclude Options",
            name: "canExcludeOptions",
            type: "Object",
        },
    ],
    extractProps({ options }) {
        const props = selectionField.extractProps(...arguments);
        props.canExcludeOptions = options.canExcludeOptions;
        return props;
    },
    fieldDependencies : ({ options }) => {
        return options.canExcludeOptions.map(o => {
            return { name : o.field, type: o.type };
        });
    },
};

registry.category("fields").add("dynamic_selection", dynamicSelectionField);
