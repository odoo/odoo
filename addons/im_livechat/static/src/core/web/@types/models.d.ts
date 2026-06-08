declare module "models" {
    export interface LivechatChannel {
        join: (param0: { notify: boolean }) => Promise<void>;
        joinTitle: Readonly<string>;
        leave: (param0: { notify: boolean }) => Promise<void>;
        leaveTitle: Readonly<string>;
    }
    export interface Store {
        goToOldestUnreadLivechatThread: () => boolean;
        has_access_livechat: boolean;
        livechatChannels: ReturnType<Store['makeCachedFetchData']>;
        livechatSelfExpertises: ReturnType<Store['makeCachedFetchData']>;
        livechatStatusButtons: Readonly<object[]>;
        pinnedLivechats: DiscussChannel[];
        show_livechat_category: boolean;
    }
    export interface Thread {
        hasFetchedLivechatSessionData: boolean;
    }
}
