import { AppointmentSyncButton } from "@appointment/components/appointment_sync_button/appointment_sync_button";
import { patch } from "@web/core/utils/patch";

patch(AppointmentSyncButton.prototype, {
    _getCalendarSyncData(calendarName) {
        if (calendarName === 'Outlook') {
            return {
                noNewEventKey: 'no_new_event_from_microsoft',
                syncRoute: '/microsoft_calendar/sync_data',
            }
        }
        return super._getCalendarSyncData(...arguments);;
    }
})
