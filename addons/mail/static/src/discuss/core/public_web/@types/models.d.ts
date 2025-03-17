declare module "models" {
    import { DiscussAppCategory as DiscussAppCategoryClass } from "@mail/discuss/core/public_web/discuss_app_category_model";

    export interface DiscussAppCategory extends DiscussAppCategoryClass {}

    export interface DiscussApp {
        allCategories: DiscussAppCategory[];
        channels: DiscussAppCategory;
        chats: DiscussAppCategory;
        computeChats: () => object;
    }
    export interface Message {
        linkedSubChannel: Thread;
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        DiscussAppCategory: StaticMailRecord<DiscussAppCategory, typeof DiscussAppCategoryClass>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        getDiscussSidebarCategoryCounter: (categoryId: string) => number;
        searchConversations: (searchValue: string) => Promise<void>;
    }
    export interface Thread {
        _computeDiscussAppCategory: () => undefined|unknown;
        createSubChannel: (param0: { initialMessage: Message, name: string }) => Promise<void>;
        discussAppCategory: DiscussAppCategory;
        displayInSidebar: boolean;
        from_message_id: Message;
        hasSubChannelFeature: Readonly<boolean>;
        lastSubChannelLoaded: Thread|null;
        loadMoreSubChannels: (param0: { searchTerm: string }) => Promise<Thread[]|undefined>;
        loadSubChannelsDone: boolean;
        parent_channel_id: Thread;
        sub_channel_ids: Thread[];
    }

    export interface Models {
        DiscussAppCategory: DiscussAppCategory;
    }
}
