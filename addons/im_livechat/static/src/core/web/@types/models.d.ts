declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory,
        livechats: Thread,
    }
    export interface Thread {
        anonymous_country: Object,
        anonymous_name: String,
        appAsLivechats: DiscussApp,
    }
}
