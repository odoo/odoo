import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class DaySelectionField extends SelectionField {
    static props = {
        ...SelectionField.props,
        monthField: String,
    };
    /**
     * @override
     * return the available days in the carryover_month
     * e.g. February -> [1, 29], april -> [1, 30]
     */
    get options() {
        let options = super.options;
        const carryover_month = this.props.record.data[this.props.monthField];
        // lastDay is the last day of the current_month for the leap year 2020
        const lastDay = new Date(2020, carryover_month, 0).getDate();
        options = options.filter((option) => option[0] <= lastDay);
        return options;
    }
}

export const daySelectionField = {
    ...selectionField,
    component: DaySelectionField,
    extractProps({ attrs }) {
        return {
            ...selectionField.extractProps(...arguments),
            monthField: attrs.month_field,
        };
    },
    fieldDependencies: ({ attrs }) => [
        {
            name: attrs.month_field,
            type: "selection",
        },
    ],
};

registry.category("fields").add("day_selection", daySelectionField);
