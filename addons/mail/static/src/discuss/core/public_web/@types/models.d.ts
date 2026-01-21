declare module "models" {
    export interface DiscussCategory {
        appCategory: DiscussAppCategory;
    }
    export interface DiscussChannel {
        _computeDiscussAppCategory: () => unknown;
        _computeIsDisplayInSidebar: () => boolean;
        appAsUnreadChannels: DiscussApp;
        autoOpenChatWindowOnNewMessage: Readonly<boolean>;
        categoryAsChannelWithCounter: DiscussAppCategory;
        createSubChannel: (param0: { initialMessage: Message, name: string }) => Promise<void>;
        discuss_category_id: DiscussCategory;
        discussAppCategory: DiscussAppCategory;
        hasSubChannelFeature: Readonly<boolean>;
        isDisplayInSidebar: boolean;
        isLocallyPinned: boolean;
        lastSubChannelLoaded: DiscussChannel;
        loadMoreSubChannels: (param0: { searchTerm: string }) => Promise<void>;
        loadSubChannelsDone: boolean;
        notifyDescriptionToServer: (description: string) => Promise<unknown>;
        notifyMessageToUser: (message: Message) => Promise<void>;
        subChannelsInSidebar: DiscussChannel[];
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        has_unpinned_channels: boolean;
        searchConversations: (searchValue: string) => Promise<void>;
    }
}
