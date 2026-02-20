declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { DiscussCategory as DiscussCategoryClass } from "@mail/discuss/core/common/discuss_category_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";

    export interface ChannelMember extends ChannelMemberClass {}
    export interface DiscussCategory extends DiscussCategoryClass {}
    export interface DiscussChannel extends DiscussChannelClass, Thread {}

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
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        channelIdsFetchingDeferred: Map<number, Deferred>;
        createGroupChat: (param0: { default_display_mode: string, name: string, user_ids: number[] }) => Promise<DiscussChannel>;
        "discuss.category": StaticMailRecord<DiscussCategory, typeof DiscussCategoryClass>;
        "discuss.channel": StaticMailRecord<DiscussChannel, typeof DiscussChannelClass>;
        "discuss.channel.member": StaticMailRecord<ChannelMember, typeof ChannelMemberClass>;
        fetchChannel: (channelId: number) => Promise<void>;
        getRecentChatPartnerIds: () => number[];
        onlineMemberStatuses: Readonly<string[]>;
        sortMembers: (m1: ChannelMember, m2: ChannelMember) => number;
        startChat: (user_ids: number[]) => Promise<void>;
        updateBusSubscription: (() => unknown) & { cancel: () => void };
    }
    export interface Thread {
        channel: DiscussChannel;
        firstUnreadMessage: Message;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        scrollUnread: boolean;
    }

    export interface Models {
        "discuss.category": DiscussCategory;
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
    }
}
