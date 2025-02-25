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
        data.mandatoryDaysList = await this.fetchSpecialDayData(data, "get_mandatory_days_data");
    },
    convertSpecialDayRecordToEvents(records) {
        const DaysList = {};
        records.forEach(
            (record) => {
                const start = luxon.DateTime.fromISO(record.start);
                const end = luxon.DateTime.fromISO(record.end);
                const duration = Math.round(end.diff(start, "days").days);
                Array.from({length: duration}, (_, index) => {
                    const day = start.plus({days: index}).toISODate()
                    DaysList[day] = {
                        title: record.title,
                        color: record.colorIndex}
                })
            }
        )
        return DaysList
    },
    async fetchSpecialDayData(data, method) {
        const records = await this.orm.call("hr.employee", method, [
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
        return this.convertSpecialDayRecordToEvents(records);
    },
});