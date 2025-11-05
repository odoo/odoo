declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        livechats: DiscussChannel[];
    }
    export interface DiscussAppCategory {
        livechat_channel_id: LivechatChannel;
    }
}
