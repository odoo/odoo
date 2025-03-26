declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        livechats: Thread[];
    }
    export interface DiscussAppCategory {
        livechat_channel_id: LivechatChannel;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
        threads: Thread[];
    }
    export interface Thread {
        anonymous_country: Country;
        appAsLivechats: DiscussApp;
        livechat_channel_id: LivechatChannel;
    }
}
