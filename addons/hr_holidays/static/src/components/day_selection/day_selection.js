import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

function getMonthField(dayField){
    const array = dayField.split("_");
    array.pop();
    if (array[array.length - 1] === 'month') {
        array.pop();
    }
    return array.join() + "_month";
};

export class DaySelectionField extends SelectionField {

    /**
     * @override
     * return the available days in the carryover_month
     * e.g. February -> [1, 29], april -> [1, 30]
     */
    get options() {
        let options = super.options;
        const carryover_month = this.props.record.data[getMonthField(this.props.name)];
        // lastDay is the last day of the current_month for the leap year 2020
        const lastDay = new Date(2020, carryover_month, 0).getDate();
        options = options.filter((option) => option[0] <= lastDay);
        return options;
    }
};

export const daySelectionField = {
    ...selectionField,
    component: DaySelectionField,
    fieldDependencies: ({ name }) => {
        return [{
            name: getMonthField(name),
            type: "selection",
        }];
    }
};

registry.category("fields").add("day_selection", daySelectionField);
