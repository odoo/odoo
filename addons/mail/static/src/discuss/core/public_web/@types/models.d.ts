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
        DiscussAppCategory: DiscussAppCategory;
        channels: unknown;
        fetchSsearchConversationsSequential: unknown;
        getDiscussSidebarCategoryCounter: (categoryId: unknown) => unknown[];
        searchConversations: (searchValue: unknown) => Promise<void>;
    }
    export interface Thread {
        _computeDiscussAppCategory: () => undefined|unknown;
        createSubChannel: ({ initialMessage: Message, name: string }) => Promise<void>;
        discussAppCategory: DiscussAppCategory;
        displayInSidebar: boolean;
        from_message_id: Message;
        hasSubChannelFeature: Readonly<boolean>;
        lastSubChannelLoaded: null;
        loadMoreSubChannels: ({ searchTerm: string }) => Promise<Thread>;
        loadSubChannelsDone: boolean;
        parent_channel_id: Thread;
        sub_channel_ids: Thread[];
    }

    export interface Models {
        DiscussAppCategory: DiscussAppCategory;
    }
}
