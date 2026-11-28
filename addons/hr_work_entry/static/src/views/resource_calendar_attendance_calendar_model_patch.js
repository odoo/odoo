import { patch } from "@web/core/utils/patch";
import { ResourceCalendarAttendanceCalendarModel } from "@resource/views/resource_calendar_attendance_calendar/resource_calendar_attendance_calendar_model";

patch(ResourceCalendarAttendanceCalendarModel.prototype, {
    /**
     * @override
     */
    getQuickAddBlockValues(rawRecord) {
        return {
            ...super.getQuickAddBlockValues(...arguments),
            work_entry_type_id: rawRecord.work_entry_type_id?.[0] || false,
        };
    },

    /**
     * @override
     */
    getQuickAddBlockTitle(record) {
        const { display_code, work_entry_type_id } = record.rawRecord;
        return display_code || work_entry_type_id?.[1] || super.getQuickAddBlockTitle(...arguments);
    },
});
