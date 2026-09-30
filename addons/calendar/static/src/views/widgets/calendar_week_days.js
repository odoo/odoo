import { registry } from "@web/core/registry";
import { WeekDays, weekDays } from "@web/views/widgets/week_days/week_days";

export class CalendarWeekDays extends WeekDays {
    static template = "calendar.WeekDays";
    onChange(day) {
        this.props.record.update({ [day]: !this.data[day] });
    }
};

export const calendarWeekDays = {
    component: CalendarWeekDays,
    fieldDependencies: weekDays.fieldDependencies,
};

registry.category("view_widgets").add("calendar_week_days", calendarWeekDays);
