declare module "models" {
    export interface DiscussChannel {
        isLocallyPinned: boolean;
        lastSubChannelLoaded: DiscussChannel;
        loadSubChannelsDone: boolean;
        messagingMenuTabs: MessagingMenuTab[];
        messagingMenuTabsWithCounter: MessagingMenuTab[];
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
        includesChannel: (channel: DiscussChannel) => boolean;
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        fetchMostPopularChannelsFetcher: ReturnType<Store['makeCachedFetchData']>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        hasHiddenChannelsFetcher: ReturnType<Store['makeCachedFetchData']>;
        most_popular_channels: DiscussChannel[];
    }
}
