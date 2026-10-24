declare module "models" {
    import { LivechatChannel as LivechatChannelClass } from "@im_livechat/core/common/livechat_channel_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface LivechatChannel extends Patch<LivechatChannelClass, typeof import("@im_livechat/core/web/livechat_channel_model_patch").livechatChannelPatch> {}
    export interface Store extends Patch<StoreClass, typeof import("@im_livechat/core/web/store_service_patch").storePatch> {
        livechatChannels: ReturnType<Store['makeCachedFetchData']>;
        livechatSelfExpertises: ReturnType<Store['makeCachedFetchData']>;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@im_livechat/core/web/thread_model_patch").threadPatch> {
        hasFetchedLivechatSessionData: boolean;
    }
}
