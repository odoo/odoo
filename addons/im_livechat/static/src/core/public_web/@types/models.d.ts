declare module "models" {
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
