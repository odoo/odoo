declare module "models" {
    import { Activity as ActivityClass } from "@mail/core/web/activity_model";

    export interface Activity extends ActivityClass {}
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

    export interface Models {
        "Activity": Activity,
    }
}
