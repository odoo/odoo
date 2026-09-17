declare module "models" {
    import { CalendarEvent as CalendarEventClass } from "@calendar/core/common/calendar_event_model";

    export interface CalendarEvent extends CalendarEventClass {}

    export interface ResPartner {
        meeting_until: import("luxon").DateTime;
        meetingStatus: Readonly<string>;
    }

    export interface Store {
        "calendar.event": StaticMailRecord<CalendarEvent, typeof CalendarEventClass>;
    }

    export interface Models {
        "calendar.event": CalendarEvent;
    }
}
