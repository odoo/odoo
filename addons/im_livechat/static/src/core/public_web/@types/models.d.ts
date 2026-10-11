declare module "models" {
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { MessagingMenu as MessagingMenuClass } from "@mail/core/public_web/messaging_menu/messaging_menu_model";

    export interface DiscussChannel extends Patch<DiscussChannelClass, typeof import("@im_livechat/core/public_web/discuss_channel_model_patch").discussChannelPatch, "autoOpenChatWindowOnNewMessage" | "inChathubOnNewMessage"> {
        appAsLivechats: DiscussApp;
        shadowedBySelf: number;
    }
    export interface MessagingMenu extends Patch<MessagingMenuClass, typeof import("@im_livechat/core/public_web/messaging_menu_model_patch").messagingMenuModelPatch> {
        livechatTab: MessagingMenuTab;
    }
}
