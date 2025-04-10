
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { serializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
patch(AttendeeCalendarModel.prototype, {
    setup() {
        super.setup(...arguments);
        this.mandatoryDays = {};
    },
    async updateData(data) {
        await super.updateData(...arguments);
        const attendeeFilters = data.filterSections.partner_ids;
        const attendeeIds = attendeeFilters.filters
            .filter((filter) => filter.type !== "all" && filter.value && filter.active)
            .map((filter) => filter.value);
        const allFilter = attendeeFilters.filters.find((filter) => filter.type === "all");
        data.mandatoryDaysList = await this.fetchSpecialDayData(data, "get_mandatory_days_data", attendeeIds, allFilter, "fa-lock");
        data.publicHolidayList = await this.fetchSpecialDayData(data, "get_public_holidays_data", attendeeIds, allFilter, "fa-plane");
    },
    convertSpecialDayRecordToEvents(records, icon) {
        const DaysList = {};
        records.forEach(
            (record) => {
                const start = luxon.DateTime.fromISO(record.start);
                const end = luxon.DateTime.fromISO(record.end);
                const duration = Math.round(end.diff(start, "days").days);
                Array.from({length: duration}, (_, index) => {
                    const day = start.plus({days: index}).toISODate()
                    if (!DaysList[day]){
                        DaysList[day] = [];
                    }
                    DaysList[day].push({
                        title: record.title,
                        color: record.colorIndex,
                        jobs_name: record.jobs_name,
                        departments_name: record.departments_name,
                        icon: icon,
                    })
                })
            }
        )
        return DaysList
    },
    async fetchSpecialDayData(data, method, attendeeIds, allFilter, icon) {
        const records = await this.orm.call("res.partner", method, [
            attendeeIds,
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
            allFilter
        ]);
        return this.convertSpecialDayRecordToEvents(records, icon);
    },
});
