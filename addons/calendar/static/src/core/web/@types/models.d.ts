declare module "models" {
    export interface Activity {
        calendar_event_id: CalendarEvent;
    }
    export interface ResUsers {
        in_meeting_until: string;
        meetingStatus: { until: string } | null;
    }
}
