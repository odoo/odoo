import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class DaySelectionField extends SelectionField {
    static props = {
        ...SelectionField.props,
    };

    /**
     * @override
     */
    get options() {
        let options = super.options;
        const carryover_month = this.props.record.data.carryover_month;
        const max_day = new Date(2023, carryover_month, 0).getDate();
        options = options.filter((option) => option[0] === "last" || option[0] < max_day);
        return options;
    }
};

export const daySelectionField = {
    ...selectionField,
    component: DaySelectionField,
    fieldDependencies: [{ name: "carryover_month", type: "selection" }],
};

registry.category("fields").add("day_selection", daySelectionField);
