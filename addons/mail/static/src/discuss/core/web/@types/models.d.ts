declare module "models" {
    import { Deferred } from "@web/core/utils/concurrency";

    export interface Store {
        fetchChannels: function;
        initChannelsUnreadCounter: number;
        hasFetchedChannels: boolean;
    }
    export interface Thread {
        foldStateCount: number,
    }
}
