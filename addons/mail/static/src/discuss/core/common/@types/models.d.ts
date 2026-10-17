declare module "models" {
    export interface Attachment {
        voice_ids: VoiceMetadata[];
    }
    export interface MailGuest {
        channelMembers: ChannelMember[];
    }
    export interface Message {
        channel_id: DiscussChannel;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        linkedSubChannel: DiscussChannel;
        threadAsFirstUnread: Thread;
    }
    export interface ResPartner {
        channelMembers: ChannelMember[];
        is_in_call: boolean|undefined;
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        companyName: string|undefined;
        favoriteChannels: DiscussChannel[];
        fetchChannelPromiseByChannelId: Map<number, Promise<DiscussChannel|void>>;
        has_hidden_channels: boolean|undefined;
        is_welcome_page_displayed: boolean|undefined;
        isChannelTokenSecret: boolean|undefined;
        updateBusSubscription: (() => unknown) & { cancel: () => void };
    }
    export interface Thread {
        channel: DiscussChannel;
        firstUnreadMessage: Message;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        scrollUnread: boolean;
    }
}
