import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
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

// fits the format "h:mm" or "-" (overridden to widen specific days when needed)
const DEFAULT_COLUMN_MIN_WIDTH = "6ch";

export class CalendarHoursByDay extends Component {
    static template = "resource.CalendarHoursByDay";
    static props = standardFieldProps;

    get isVariable() {
        return this.props.record.data.calendar_type === "variable";
    }

    get attendances() {
        return this.props.record.data[this.props.name]?.records || [];
    }

    get columnWidths() {
        return WEEKDAY_LABELS.map(() => DEFAULT_COLUMN_MIN_WIDTH);
    }

    get gridTemplateColumns() {
        return this.columnWidths.map((minWidth) => `minmax(${minWidth}, 1fr)`).join(" ");
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
        const days = new Set();
        let hours = 0;
        for (const attendance of this.attendances) {
            const { date, duration_hours } = attendance.data;
            if (date) {
                days.add(date.toISODate());
            }
            hours += duration_hours;
        }
        return _t("Variable (%(days)s days - %(hours)sh)", {
            days: days.size,
            hours: hours % 1 === 0 ? hours : hours.toFixed(1),
        });
    }
}

export const calendarHoursByDay = {
    component: CalendarHoursByDay,
    displayName: _t("Working Hours by Day"),
    supportedTypes: ["one2many"],
    fieldDependencies: [{ name: "calendar_type", type: "selection" }],
    relatedFields: () => [
        { name: "dayofweek", type: "selection" },
        { name: "date", type: "date" },
        { name: "duration_hours", type: "float" },
    ],
};

registry.category("fields").add("resource_calendar_hours_by_day", calendarHoursByDay);
