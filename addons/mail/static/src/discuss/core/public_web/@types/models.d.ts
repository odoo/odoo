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
        compareChannels: (c1: DiscussChannel, c2: DiscussChannel) => number;
        getSortedChannels: (filter: import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter, channels: DiscussChannel[]) => DiscussChannel[];
        includesChannel: (channel: DiscussChannel) => boolean;
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        fetchMostPopularChannelsFetcher: ReturnType<Store['makeCachedFetchData']>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        hasHiddenChannelsFetcher: ReturnType<Store['makeCachedFetchData']>;
        most_popular_channels: DiscussChannel[];
        searchConversations: (searchValue: string) => Promise<void>;
    }
}
