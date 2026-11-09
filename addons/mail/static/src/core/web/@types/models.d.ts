declare module "models" {
    import { FollowerListView as FollowerListViewClass } from "@mail/core/web/follower_list_view_model";

    export interface Activity {
        dateCreateFormatted: Readonly<string>;
        dateDeadlineFormatted: Readonly<string>;
        dateDoneFormatted: Readonly<string>;
        edit: () => Promise<void>;
        isNoteEmpty: boolean;
        markAsDone: (attachmentIds: number[]) => Promise<void>;
        markAsDoneAndScheduleNext: () => Promise<import("@web/webclient/actions/action_plugin").ActionDescription>;
        remove: (param0: { broadcast: boolean }) => void;
    }
    export interface FollowerListView extends FollowerListViewClass {}
    export interface Message {
        canForward: Readonly<boolean>;
        canReplyAll: Readonly<boolean>;
    }
    export interface Models {
        FollowerListView: FollowerListView;
    }
    export interface Store {
        FollowerListView: StaticMailRecord<FollowerListView, typeof FollowerListViewClass>;
        _onActivityBroadcastChannelMessage: (param0: { data: { type: "INSERT"|"DELETE"|"RELOAD_CHATTER", payload: Partial<Activity> } }) => void;
        activities_to_assign_count: undefined;
        activity_counter_bus_id: number;
        activity_groups: Object[];
        activityBroadcastChannel: BroadcastChannel|null;
        activityCounter: number;
        activityGroups: Readonly<unknown[]>;
        markNeedactionMessagesAsRead: () => Promise<void>;
        messagingMenuSystrayState: MessagingMenuUIState;
        onLinkFollowed: (fromThread: Thread) => void;
        onUpdateActivityGroups: () => void;
        removeAllBookmarks: () => Promise<void>;
        scheduleActivity: (resModel: string, resIds: number[], defaultActivityTypeId: number|undefined) => Promise<void>;
        updateAppBadge: () => void;
    }
    export interface Thread {
        follow: () => Promise<void>;
        openRecordActionRequest: Readonly<object>;
    }
}
