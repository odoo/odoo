declare module "models" {
    import { DiscussCategory as DiscussCategoryClass } from "@mail/discuss/core/public_web/discuss_category_model";

    export interface DiscussCategory extends DiscussCategoryClass {}

    export interface DiscussChannel {
        _computeIsDisplayInSidebar: () => boolean;
        allowedToLeaveChannelTypes: Readonly<string[]>;
        allowedToUnpinChannelTypes: Readonly<string[]>;
        canLeave: Readonly<boolean>;
        canUnpin: Readonly<boolean>;
        discuss_category_id: DiscussCategory;
        displayToSelf: boolean;
        isDisplayInSidebar: boolean;
        notifyDescriptionToServer: (description: string) => Promise<unknown>;
        notifyMessageToUser: (message: Message) => Promise<void>;
        subChannelsInSidebar: Thread[];
    }
    export interface Message {
        linkedSubChannel: Thread;
    }
    export interface Store {
        channels: ReturnType<Store['makeCachedFetchData']>;
        "discuss.category": StaticMailRecord<DiscussCategory, typeof DiscussCategoryClass>;
        fetchSsearchConversationsSequential: () => Promise<any>;
        searchConversations: (searchValue: string) => Promise<void>;
    }
    export interface Thread {
        _computeDiscussAppCategory: () => unknown;
        appAsUnreadChannels: DiscussApp;
        categoryAsThreadWithCounter: DiscussAppCategory;
        createSubChannel: (param0: { initialMessage: Message, name: string }) => Promise<void>;
        discussAppCategory: DiscussAppCategory;
        from_message_id: Message;
        hasSubChannelFeature: Readonly<boolean>;
        lastSubChannelLoaded: Thread|null;
        loadMoreSubChannels: (param0: { searchTerm: string }) => Promise<Thread[]|undefined>;
        loadSubChannelsDone: boolean;
        parent_channel_id: Thread;
        sub_channel_ids: Thread[];
    }

    export interface Models {
        "discuss.category": DiscussCategory;
    }
}
