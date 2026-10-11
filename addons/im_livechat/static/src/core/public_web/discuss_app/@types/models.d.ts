declare module "models" {
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app/discuss_app_model";

    export interface DiscussApp extends Patch<DiscussAppClass, typeof import("@im_livechat/core/public_web/discuss_app/discuss_app_model_patch").discussAppPatch> {
        isLivechatInfoPanelOpenByDefault: boolean;
        livechats: DiscussChannel[];
    }
}
