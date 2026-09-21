import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export const WEEKDAY_LABELS = [
    _t("Monday"),
    _t("Tuesday"),
    _t("Wednesday"),
    _t("Thursday"),
    _t("Friday"),
    _t("Saturday"),
    _t("Sunday"),
];

export function formatHoursLabel(hours) {
    if (!hours) {
        return "-";
    }
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    return `${wholeHours}:${String(minutes).padStart(2, "0")}`;
}

export class CalendarHoursByDay extends Component {
    static template = "resource.CalendarHoursByDay";

    props = useProps(standardFieldProps);

    get isVariable() {
        return this.props.record.data.calendar_type === "variable";
    }

    get attendances() {
        return this.props.record.data[this.props.name]?.records || [];
    }

    // sums durations of fixed schedules per day of the week (Monday -> Sunday)
    get hoursByDay() {
        const hoursByDay = [0, 0, 0, 0, 0, 0, 0];
        for (const attendance of this.attendances) {
            const { dayofweek, date, duration_hours } = attendance.data;
            if (date) {
                // ignore variable schedules (date-specific attendances)
                continue;
            }
            hoursByDay[Number(dayofweek)] += duration_hours;
        }
        return hoursByDay.map((hours, index) => ({
            hours: formatHoursLabel(hours),
            label: WEEKDAY_LABELS[index],
        }));
    }

    get variableScheduleSummary() {
        const hours_per_week = this.props.record.data.hours_per_week;
        return _t("Variable (%(hours)sh on %(days)s days / week)", {
            hours: hours_per_week % 1 === 0 ? hours_per_week : hours_per_week.toFixed(1),
            days: this.props.record.data.days_per_week,
        });
    }
}

export const calendarHoursByDay = {
    component: CalendarHoursByDay,
    displayName: _t("Working Hours by Day"),
    supportedTypes: ["one2many"],
    fieldDependencies: [
        { name: "calendar_type", type: "selection" },
        { name: "days_per_week", type: "float" },
        { name: "hours_per_week", type: "float" },
    ],
    relatedFields: () => [
        { name: "dayofweek", type: "selection" },
        { name: "date", type: "date" },
        { name: "duration_hours", type: "float" },
    ],
};

registry.category("fields").add("resource_calendar_hours_by_day", calendarHoursByDay);
