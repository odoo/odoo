declare module "models" {
    export interface Store {
        getSelfImportantChannels: () => Thread[];
        getSelfRecentChannels: () => Thread[];
        initChannelsUnreadCounter: number;
    }
}
