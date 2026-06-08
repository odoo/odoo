declare module "models" {
    import { DiscussAppCategory as DiscussAppCategoryClass } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";

    export interface DiscussAppCategory extends DiscussAppCategoryClass {}

    export interface DiscussApp {
        allCategories: DiscussAppCategory[];
        channelCategory: DiscussAppCategory;
        chatCategory: DiscussAppCategory;
        computeChatCategory: () => object;
        favoriteCategory: DiscussAppCategory;
        unreadChannels: DiscussChannel[];
    }
    export interface Store {
        DiscussAppCategory: StaticMailRecord<DiscussAppCategory, typeof DiscussAppCategoryClass>;
    }

    export interface Models {
        DiscussAppCategory: DiscussAppCategory;
    }
}
