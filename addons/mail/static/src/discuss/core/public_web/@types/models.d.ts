declare module "models" {
    export interface DiscussChannel {
        _computeMessagingMenuTabsWithCounter: () => unknown[];
        autoOpenChatWindowOnNewMessage: Readonly<boolean>;
        createSubChannel: (param0: { initialMessage: Message, name: string }) => Promise<void>;
        hasSubChannelFeature: Readonly<boolean>;
        inChathubOnNewMessage: Readonly<boolean>;
        isLocallyPinned: boolean;
        lastSubChannelLoaded: DiscussChannel;
        loadMoreSubChannels: (param0: { searchTerm: string }) => Promise<void>;
        loadSubChannelsDone: boolean;
        messagingMenuTabs: MessagingMenuTab[];
        messagingMenuTabsWithCounter: MessagingMenuTab[];
        notifyDescriptionToServer: (description: string) => Promise<unknown>;
        notifyMessageToUser: (message: Message) => Promise<void>;
        primaryMessagingMenuTab: MessagingMenuTab;
    }
    export interface MessagingMenu {
        channelTab: MessagingMenuTab;
        chatTab: MessagingMenuTab;
        meetingTab: MessagingMenuTab;
    }
    export interface MessagingMenuTab {
        channels: DiscussChannel[];
        channelsWithCounter: DiscussChannel[];
        matchesChannel: () => boolean;
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        fetchMostPopularChannelsFetcher: ReturnType<Store['makeCachedFetchData']>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        most_popular_channels: DiscussChannel[];
        searchConversations: (searchValue: string) => Promise<void>;
    }
}
