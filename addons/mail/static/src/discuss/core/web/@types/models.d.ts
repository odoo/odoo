declare module "models" {
    import { Deferred } from "@web/core/utils/concurrency";
    import { Store as StoreClass } from "@mail/core/common/store_service";

    export interface Store {
        initChannelsUnreadCounter: number;
        channels: ReturnType<StoreClass["makeCachedFetchData"]>;
    }
    export interface Thread {
        fetchChannelInfoDeferred: Promise<Thread>;
        fetchChannelInfoState: 'not_fetched' | 'fetching' | 'fetched';
        fetchChannelInfo: function;
        foldStateCount: number,
    }
}
