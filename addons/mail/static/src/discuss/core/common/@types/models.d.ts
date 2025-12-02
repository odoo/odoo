declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";

    export interface ChannelMember extends ChannelMemberClass {}
    export interface DiscussChannel extends DiscussChannelClass, Thread {}

    export interface MailGuest {
        channelMembers: ChannelMember[];
    }
    export interface Message {
        channel_id: DiscussChannel;
        channelMemberHaveSeen: Readonly<ChannelMember[]>;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneFetched: boolean|undefined;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        showSeenIndicator: (thread: Thread) => boolean;
        threadAsFirstUnread: Thread;
    }
    export interface ResPartner {
        channelMembers: ChannelMember[];
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        channelIdsFetchingDeferred: Map<number, Deferred>;
        createGroupChat: (param0: { default_display_mode: string, partners_to: number[], name: string }) => Promise<DiscussChannel>;
        "discuss.channel": StaticMailRecord<DiscussChannel, typeof DiscussChannelClass>;
        "discuss.channel.member": StaticMailRecord<ChannelMember, typeof ChannelMemberClass>;
        fetchChannel: (channelId: number) => Promise<void>;
        getRecentChatPartnerIds: () => number[];
        onlineMemberStatuses: Readonly<string[]>;
        sortMembers: (m1: ChannelMember, m2: ChannelMember) => number;
        startChat: (partnerIds: number[]) => Promise<void>;
        updateBusSubscription: (() => unknown) & { cancel: () => void };
    }
    export interface Thread {
        allowedToLeaveChannelTypes: Readonly<string[]>;
        allowedToUnpinChannelTypes: Readonly<string[]>;
        avatar_cache_key: string;
        canLeave: Readonly<boolean>;
        canUnpin: Readonly<boolean>;
        channel: DiscussChannel;
        channel_name_member_ids: ChannelMember[];
        computeCorrespondent: () => ChannelMember;
        correspondent: ChannelMember;
        correspondentCountry: Country;
        correspondents: Readonly<ChannelMember[]>;
        executeCommand: (command: unknown, body: string) => unknown;
        fetchMoreAttachments: (limit: number) => Promise<void>;
        firstUnreadMessage: Message;
        group_ids: ResGroups[];
        leaveChannel: () => Promise<void>;
        leaveChannelRpc: () => void;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        name: string;
        notifyAvatarToServer: (data: string) => Promise<void>;
        notifyDescriptionToServer: (description: unknown) => Promise<unknown>;
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        showCorrespondentCountry: Readonly<boolean>;
        showUnreadBanner: Readonly<boolean>;
    }

    export interface Models {
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
    }
}
