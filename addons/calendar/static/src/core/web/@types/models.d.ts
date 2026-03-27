declare module "models" {
    export interface Activity {
        rescheduleMeeting: () => Promise<void>;
    }
    export interface ResUsers {
        in_meeting_until: string;
        meetingStatus: { until: string } | null;
    }
}
