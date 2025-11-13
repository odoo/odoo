declare module "models" {
    export interface Activity {
        dateCreateFormatted: Readonly<string>;
        dateDeadlineFormatted: Readonly<string>;
        dateDoneFormatted: Readonly<string>;
        edit: () => Promise<void>;
        markAsDone: (attachmentIds: number[]) => Promise<void>;
        markAsDoneAndScheduleNext: () => Promise<ActionDescription>;
        remove: (param0: { broadcast: boolean }) => void;
    }
    export interface Message {
        canForward: (thread: Thread) => boolean;
        canReplyAll: (thread: Thread) => boolean;
    }
    export interface Store {
        _onActivityBroadcastChannelMessage: (param0: { data: { type: "INSERT"|"DELETE"|"RELOAD_CHATTER", payload: Partial<Activity> } }) => void;
        activity_counter_bus_id: number;
        activityCounter: number;
        activityGroups: Object[];
        history: Thread;
        inbox: Thread;
        onLinkFollowed: (fromThread: Thread) => void;
        onUpdateActivityGroups: () => void;
        scheduleActivity: (resModel: string, resIds: number[], defaultActivityTypeId: number|undefined) => Promise<void>;
        starred: Thread;
        unstarAll: () => Promise<void>;
    }
    export interface Thread {
        activities: Activity[];
        follow: () => Promise<void>;
        isDisplayedInDiscussAppDesktop: boolean;
        loadMoreFollowers: () => Promise<void>;
        loadMoreRecipients: () => Promise<void>;
        recipients: Follower[];
        recipientsCount: number|undefined;
        recipientsFullyLoaded: Readonly<boolean>;
    }
}
