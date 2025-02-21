declare module "models" {
    export interface Activity {
        rescheduleMeeting: () => Promise<void>;
    }
}
