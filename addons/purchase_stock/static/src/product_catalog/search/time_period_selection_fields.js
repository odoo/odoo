import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { selectionField, SelectionField } from "@web/views/fields/selection/selection_field";

const { DateTime } = luxon;

export class TimePeriodSelectionField extends SelectionField {
    static props = {
        ...SelectionField.props,
        onChange: { type: Function, optional: true },
    };

    onChange(ev) {
        super.onChange(ev);
        if (this.props.onChange) {
            this.props.onChange(ev);
        }
    }

    get options() {
        // This field widget replaces three last options of `based_on` field by
        // the current month, the next month and the after next month for the
        // last year. For instance, if the current date is 12 January 2025,
        // the options will be "January 2024", "February 2024" and "March 2024".
        const date1 = DateTime.now().set({ day: 1 }).minus({ years: 1 });
        const date2 = date1.plus({ months: 1 });
        const date3 = date1.plus({ months: 2 });
        const options = [];
        for (const option of this.props.record.fields[this.props.name].selection) {
            if (option[0] === "last_year") {
                options.push([option[0], `${date1.monthLong} ${date1.year}`]);
            } else if (option[0] === "last_year_m_plus_1") {
                options.push([option[0], `${date2.monthLong} ${date2.year}`]);
            } else if (option[0] === "last_year_m_plus_2") {
                options.push([option[0], `${date3.monthLong} ${date3.year}`]);
            } else if (option[0] === "last_year_quarter") {
                let beginDate = date1.monthShort;
                const endDate = `${date3.monthShort} ${date3.year}`;
                if (date1.year !== date3.year) {
                    beginDate += ` ${date1.year}`;
                }
                options.push([option[0], `${beginDate}-${endDate}`]);
            } else if (option[0] !== false && option[1] !== "") {
                options.push(option);
            }
        }
        return options;
    }
}

export const timePeriodSelectionField = {
    ...selectionField,
    component: TimePeriodSelectionField,
    displayName: _t("Time Perdiod Selection"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("time_period_selection", timePeriodSelectionField);
