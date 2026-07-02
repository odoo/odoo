import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarModel } from "@web/views/calendar/calendar_model";

export class DailyRatesCalendarModel extends CalendarModel {
    // UX: hide the popup time picker
    get showMultiCreateTimeRange() {
        return false;
    }
    // route via getAllDayDates
    buildRawRecord(partialRecord, options = {}) {
        return super.buildRawRecord({ ...partialRecord, isAllDay: true }, options);
    }
    // whole day: midnight -> next midnight
    getAllDayDates(start, end = start) {
        const s = start.startOf("day");
        let e = end.startOf("day");
        if (e <= s) {
            e = s.plus({ days: 1 });
        }
        return [s, e];
    }
}

registry
    .category("views")
    .add("daily_rates_calendar", {
        ...calendarView,
        Model: DailyRatesCalendarModel,
    });
