declare module "models" {
    import { Deferred } from "@web/core/utils/concurrency";
    import { Store as StoreClass } from "@mail/core/common/store_service";

    export interface Store {
        fetchChannels: function;
        initChannelsUnreadCounter: number;
        channels: ReturnType<StoreClass["makeCachedFetchData"]>;
    }
    export interface Thread {
        foldStateCount: number,
    }
}
