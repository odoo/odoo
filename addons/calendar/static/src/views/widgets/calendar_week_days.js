import { registry } from "@web/core/registry";
import { WeekDays, weekDays } from "@web/views/widgets/week_days/week_days";
import { localization } from "@web/core/l10n/localization";
import { pyToJsLocale } from "@web/core/l10n/utils/locales";

export class CalendarWeekDays extends WeekDays {
    static template = "calendar.WeekDays";
    onChange(day) {
        this.props.record.update({ [day]: !this.data[day] });
    }

    getWeekDay(dayIndex) {
        return luxon.Info.weekdays(
            "narrow",
            { locale: pyToJsLocale(localization.code) }
        )[(dayIndex + localization.weekStart - 1) % 7];
    }
};

export const calendarWeekDays = {
    component: CalendarWeekDays,
    fieldDependencies: weekDays.fieldDependencies,
};

registry.category("view_widgets").add("calendar_week_days", calendarWeekDays);
