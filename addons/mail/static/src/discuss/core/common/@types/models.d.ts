declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { DiscussCategory as DiscussCategoryClass } from "@mail/discuss/core/common/discuss_category_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";
    import { VoiceMetadata as VoiceMetadataClass } from "@mail/discuss/core/common/voice_metadata_model";

    export interface ChannelMember extends ChannelMemberClass {}
    export interface DiscussCategory extends DiscussCategoryClass {}
    export interface DiscussChannel extends DiscussChannelClass, Thread {}
    export interface VoiceMetadata extends VoiceMetadataClass {}

    export interface Attachment {
        voice_ids: VoiceMetadata[];
    }
    export interface MailGuest {
        channelMembers: ChannelMember[];
    }
    export interface Message {
        channel_id: DiscussChannel;
        channelMemberHaveSeen: Readonly<ChannelMember[]>;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        linkedSubChannel: DiscussChannel;
        showSeenIndicator: (thread: Thread) => boolean;
        threadAsFirstUnread: Thread;
    }
    export interface ResPartner {
        channelMembers: ChannelMember[];
        is_in_call: boolean|undefined;
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        companyName: string|undefined;
        createGroupChat: (param0: { default_display_mode: string, users_to: number[], name: string }) => Promise<DiscussChannel>;
        "discuss.category": StaticMailRecord<DiscussCategory, typeof DiscussCategoryClass>;
        "discuss.channel": StaticMailRecord<DiscussChannel, typeof DiscussChannelClass>;
        "discuss.channel.member": StaticMailRecord<ChannelMember, typeof ChannelMemberClass>;
        "discuss.voice.metadata": StaticMailRecord<VoiceMetadata, typeof VoiceMetadataClass>;
        favoriteChannels: DiscussChannel[];
        fetchChannel: (channelId: number, param0: { with_last_message: boolean }) => Promise<void>;
        fetchChannelPromiseByChannelId: Map<number, Promise<DiscussChannel|void>>;
        getRecentChatPartnerIds: () => number[];
        has_hidden_channels: boolean|undefined;
        is_welcome_page_displayed: boolean|undefined;
        isChannelTokenSecret: boolean|undefined;
        sortMembers: (m1: ChannelMember, m2: ChannelMember) => number;
        startChat: (partnerIds: number[]) => Promise<Thread>;
        updateBusSubscription: (() => unknown) & { cancel: () => void };
    }
    export interface Thread {
        channel: DiscussChannel;
        firstUnreadMessage: Message;
        handleMarkAsRead: (newestPersistentMessage: Message, wasMarkedAsUnread: boolean) => Promise<undefined|unknown>;
        isReadBySelf: (message: Message) => boolean;
        markAsReadRpc: (newestPersistentMessage: Message) => unknown;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        scrollUnread: boolean;
    }

    export interface Models {
        "discuss.category": DiscussCategory;
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
        "discuss.voice.metadata": VoiceMetadata;
    }
}
