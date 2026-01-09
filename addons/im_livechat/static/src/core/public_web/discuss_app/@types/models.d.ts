declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        isLivechatInfoPanelOpenByDefault: boolean;
        lastThread: Thread;
        livechatLookingForHelpCategory: DiscussAppCategory;
        livechats: DiscussChannel[];
    }
    export interface DiscussAppCategory {
        livechat_channel_id: LivechatChannel;
    }
}
