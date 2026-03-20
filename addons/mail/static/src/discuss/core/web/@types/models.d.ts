declare module "models" {
    export interface DiscussChannel {
        isDisplayedInDiscussAppDesktop: boolean;
    }
    export interface Store {
        getSelfImportantChannels: () => DiscussChannel[];
        getSelfRecentChannels: () => DiscussChannel[];
        initChannelsUnreadCounter: number;
    }
}
