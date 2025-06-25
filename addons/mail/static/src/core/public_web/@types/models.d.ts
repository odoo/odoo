declare module "models" {
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app_model";
    import { DiscussAppCategory as DiscussAppCategoryClass } from "@mail/core/public_web/discuss_app_category_model";

    export interface DiscussApp extends DiscussAppClass { }
    export interface DiscussAppCategory extends DiscussAppCategoryClass { }
    export interface Store {
        DiscussApp: DiscussApp,
        DiscussAppCategory : DiscussAppCategory,
        discuss: DiscussApp,
        action_discuss_id: number,
        getDiscussSidebarCategoryCounter: (categoryId: number) => number,
    }

    export interface Thread {
        discussAppCategory: DiscussAppCategory,
        setAsDiscussThread: (pushState: boolean) => void,
        unpin: () => Promise<void>,
    }

    export interface Models {
        "DiscussApp": DiscussApp,
        "DiscussAppCategory": DiscussAppCategory,
    }
}
