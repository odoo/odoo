declare module "models" {
    export interface DiscussChannel {
        isDisplayedInDiscussAppDesktop: boolean;
    }
    export interface Store {
        getSelfImportantChannels: () => DiscussChannel[];
        getSelfRecentChannels: () => DiscussChannel[];
        init_unread_channel_ids: number[];
    }
}
