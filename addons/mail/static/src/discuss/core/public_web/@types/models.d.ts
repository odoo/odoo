declare module "models" {
    import { DiscussAppCategory as DiscussAppCategoryClass } from "@mail/discuss/core/public_web/discuss_app_category_model";

    export interface DiscussAppCategory extends DiscussAppCategoryClass { }
    export interface Store {
        DiscussAppCategory : DiscussAppCategory,
    }
    export interface Thread {
        discussAppCategory: DiscussAppCategory,
        _computeDiscussAppCategory(): DiscussAppCategory,
    }
    export interface DiscussApp {
        allCategories: DiscussAppCategory[];
        channels: DiscussAppCategory;
        chats: DiscussAppCategory;
    }
    export interface Store {
        getDiscussSidebarCategoryCounter: (categoryId: number) => number,
    }
    export interface Thread {
        displayInSidebar: boolean;
        from_message_id: Message;
        parent_channel_id: Thread;
        readonly hasSubChannelFeature: boolean;
        sub_channel_ids: Thread[];
    }

    export interface Models {
        "DiscussAppCategory": DiscussAppCategory,
    }
}
