declare module "models" {
    export interface Thread {
        scheduledMessages: ScheduledMessage[];
        sortedScheduledMessages: ScheduledMessage[];
    }
}
