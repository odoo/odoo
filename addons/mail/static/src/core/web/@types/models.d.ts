declare module "models" {
    export interface Activity {
        isNoteEmpty: boolean;
    }
    export interface Store {
        activities_to_assign_count: undefined;
        activity_counter_bus_id: number;
        activity_groups: Object[];
        activityBroadcastChannel: BroadcastChannel|null;
        activityCounter: number;
        messagingMenuSystrayState: MessagingMenuUIState;
    }
}
