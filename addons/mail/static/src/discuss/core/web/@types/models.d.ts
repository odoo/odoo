declare module "models" {
    import { Deferred } from "@web/core/utils/concurrency";

    export interface Store {
        fetchChannelsState: 'not_fetched' | 'fetching' | 'fetched';
        fetchChannelsDeferred: Deferred;
        fetchChannels: function;
        initChannelsUnreadCounter: number;
    }
    export interface Thread {
        foldStateCount: number,
    }
}
