declare module "models" {
    export interface Store {
        getSelfImportantChannels: () => DiscussChannel[];
        getSelfRecentChannels: () => DiscussChannel[];
        initChannelsUnreadCounter: number;
        onClickPartnerMention: (ev: MouseEvent, id: number) => void;
    }
}
