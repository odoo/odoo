declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        livechats: DiscussChannel[];
    }
    export interface DiscussAppCategory {
        livechat_channel_id: LivechatChannel;
    }
    export interface DiscussChannel {
        appAsLivechats: DiscussApp;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
    }
    export interface Thread {
        country_id: Country;
    }
}
