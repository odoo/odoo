import { Component } from "@odoo/owl";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";

export class CalendarSidePanel extends Component {
    static components = {
        DatePicker: DateTimePicker,
        FilterSection: CalendarFilterSection,
    };
    static template = "web.CalendarSidePanel";
    static props = ["model"];

    get datePickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            onSelect: (date) => {
                let scale = "week";

                if (this.props.model.date.hasSame(date, "day")) {
                    const scales = ["month", "week", "day"];
                    scale = scales[(scales.indexOf(this.props.model.scale) + 1) % scales.length];
                } else {
                    // Check if dates are on the same week
                    // As a.hasSame(b, "week") does not depend on locale and week always starts on Monday,
                    // we are comparing derivated dates instead to take this into account.
                    const currentDate =
                        this.props.model.date.weekday === 7
                            ? this.props.model.date.plus({ day: 1 })
                            : this.props.model.date;
                    const pickedDate = date.weekday === 7 ? date.plus({ day: 1 }) : date;

                    // a.hasSame(b, "week") does not depend on locale and week alway starts on Monday
                    if (currentDate.hasSame(pickedDate, "week")) {
                        scale = "day";
                    }
                }

                this.props.model.load({ scale, date });
            },
            value: this.props.model.date,
        };
    }
    get filterPanelProps() {
        return {
            model: this.props.model,
        };
    }

    get showDatePicker() {
        return this.props.model.showDatePicker && !this.env.isSmall;
    }
}
