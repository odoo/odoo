declare module "models" {
    export interface DiscussApp {
        defaultLivechatCategory: DiscussAppCategory,
        livechats: Thread,
    }
    export interface Thread {
        anonymous_country: Country,
        anonymous_name: String,
        appAsLivechats: DiscussApp,
    }
    export interface Store {
        has_access_livechat: boolean,
    }
    export interface LivechatChannel {
        threads: Thread[],
    }
}
