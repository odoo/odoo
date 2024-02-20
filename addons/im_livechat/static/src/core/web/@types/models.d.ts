declare module "models" {
    export interface DiscussApp {
        livechatThreads: Thread,
        defaultLivechatCategory: DiscussAppCategory,
    }
    export interface Thread {
        anonymous_country: Object,
        anonymous_name: String,
        appAsLivechat: DiscussApp,
    }
    export interface DiscussAppCategory {
        isLivechatCategory: Boolean,
    }
}
