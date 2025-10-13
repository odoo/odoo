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
        appAsLivechats: DiscussApp;
        country_id: Country;
        livechat_channel_id: LivechatChannel;
    }
}
