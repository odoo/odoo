/** @odoo-module **/

const { Component, onMounted, onWillUnmount, useEffect, useRef, xml } = owl;
const { DateTime, Info } = luxon;

export class CalendarDatePicker extends Component {
    setup() {
        this.rootRef = useRef("root");
        onMounted(() => {
            this.$el.datepicker(this.options);
        });
        useEffect(() => {
            this.highlight();
        });
        onWillUnmount(() => {
            this.$el.datepicker("destroy");
            const picker = document.querySelector("#ui-datepicker-div:empty");
            if (picker) {
                picker.remove();
            }
        });
    }

    get options() {
        // this is needed because luxon gives the week in ISO format : Monday is the first day of the week.
        // (M T W T F S S) but the jsquery datepicker wants as day name option in US format (S M T W T F S)
        const weekdays = Array.from(Info.weekdays("narrow"));
        const last = weekdays.pop();
        return {
            dayNamesMin: [last, ...weekdays],
            firstDay: (this.props.model.firstDayOfWeek || 0) % 7,
            monthNames: Info.months("short"),
            onSelect: this.onDateSelected.bind(this),
            showOtherMonths: true,
            dateFormat: "yy-mm-dd",
        };
    }
    get $el() {
        return $(this.rootRef.el);
    }

    highlight() {
        this.$el
            .datepicker("setDate", this.props.model.date.toFormat("yyyy-MM-dd"))
            .find(".o_selected_range")
            .removeClass("o_color o_selected_range");
        let $a;
        switch (this.props.model.scale) {
            case "year":
                $a = this.$el.find("td");
                break;
            case "month":
                $a = this.$el.find("td");
                break;
            case "week":
                $a = this.$el.find("tr:has(.ui-state-active)");
                break;
            case "day":
                $a = this.$el.find("a.ui-state-active");
                break;
        }
        $a.addClass("o_selected_range");
        $a.not(".ui-state-active").addClass("o_color");

        // Correctly highlight today
        // This is needed in case the user's local timezone is different from the system one
        const { year, month, day } = DateTime.local();
        this.$el.find(".ui-datepicker-today").removeClass("ui-datepicker-today");
        this.$el
            .find(`td[data-year="${year}"][data-month="${month - 1}"]:contains("${day}")`)
            .addClass("ui-datepicker-today");
    }

    onDateSelected(_, info) {
        const model = this.props.model;
        const date = DateTime.local(+info.currentYear, +info.currentMonth + 1, +info.currentDay);
        let scale = "week";

        if (model.date.hasSame(date, "day")) {
            const scales = ["month", "week", "day"];
            scale = scales[(scales.indexOf(model.scale) + 1) % scales.length];
        } else {
            // Check if dates are on the same week
            // As a.hasSame(b, "week") does not depend on locale and week always starts on Monday,
            // we are comparing derivated dates instead to take this into account.
            const currentDate = model.date.weekday === 7 ? model.date.plus({ day: 1 }) : model.date;
            const pickedDate = date.weekday === 7 ? date.plus({ day: 1 }) : date;

            // a.hasSame(b, "week") does not depend on locale and week alway starts on Monday
            if (currentDate.hasSame(pickedDate, "week")) {
                scale = "day";
            }
        }

        model.load({ scale, date });
    }
}
CalendarDatePicker.props = {
    model: Object,
};
CalendarDatePicker.template = xml`<div class="o_calendar_mini" t-ref="root" />`;
