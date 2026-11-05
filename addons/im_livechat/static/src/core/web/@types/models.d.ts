declare module "models" {
    export interface BrowsingHistoryEntry {
        title: string;
        url: string;
        visit_datetime: string;
    }

    export interface DiscussChannel {
        browsingHistory: BrowsingHistoryEntry[];
        browsingHistoryStatus: "idle"|"loading"|"ready"|"error"|"unavailable";
    }
    export interface LivechatChannel {
        join: (param0: { notify: boolean }) => Promise<void>;
        joinTitle: Readonly<string>;
        leave: (param0: { notify: boolean }) => Promise<void>;
        leaveTitle: Readonly<string>;
    }
    export interface Store {
        goToOldestUnreadLivechatThread: () => boolean;
        livechatChannels: ReturnType<Store['makeCachedFetchData']>;
        livechatSelfExpertises: ReturnType<Store['makeCachedFetchData']>;
        livechatStatusButtons: Readonly<object[]>;
    }
    export interface Thread {
        hasFetchedLivechatSessionData: boolean;
    }
}
