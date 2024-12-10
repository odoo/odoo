declare module "models" {
    export interface Discuss  {
        inbox: Thread,
        stared: Thread,
        history: Thread,
    }
    export interface Store {
        activityCounter: number,
        activity_counter_bus_id: number,
        activityGroups: Object[],
    }
    export interface Thread {
        recipients: Follower[],
    }
}
