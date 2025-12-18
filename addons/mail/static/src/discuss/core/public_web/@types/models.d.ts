declare module "models" {
    import { DiscussCategory as DiscussCategoryClass } from "@mail/discuss/core/public_web/discuss_category_model";

    export interface DiscussCategory extends DiscussCategoryClass {}

    export interface DiscussChannel {
        _computeDiscussAppCategory: () => unknown;
        _computeIsDisplayInSidebar: () => boolean;
        appAsUnreadChannels: DiscussApp;
        categoryAsChannelWithCounter: DiscussAppCategory;
        discuss_category_id: DiscussCategory;
        discussAppCategory: DiscussAppCategory;
        isDisplayInSidebar: boolean;
        isLocallyPinned: boolean;
        notifyDescriptionToServer: (description: string) => Promise<unknown>;
        notifyMessageToUser: (message: Message) => Promise<void>;
        subChannelsInSidebar: DiscussChannel[];
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        "discuss.category": StaticMailRecord<DiscussCategory, typeof DiscussCategoryClass>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        has_unpinned_channels: boolean;
        searchConversations: (searchValue: string) => Promise<void>;
    }
    export interface Thread {
        createSubChannel: (param0: { initialMessage: Message, name: string }) => Promise<void>;
        hasSubChannelFeature: Readonly<boolean>;
        lastSubChannelLoaded: DiscussChannel;
        loadMoreSubChannels: (param0: { searchTerm: string }) => Promise<void>;
        loadSubChannelsDone: boolean;
    }

    export interface Models {
        "discuss.category": DiscussCategory;
    }
}
