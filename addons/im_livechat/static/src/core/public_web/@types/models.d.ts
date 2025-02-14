declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory;
        livechats: Thread[];
    }
    export interface DiscussAppCategory {
        livechatChannel: LivechatChannel;
    }
    export interface LivechatChannel {
        appCategory: DiscussAppCategory;
        threads: Thread[];
    }
    export interface Thread {
        anonymous_country: Country;
        appAsLivechats: DiscussApp;
        livechatChannel: LivechatChannel;
    }
}
