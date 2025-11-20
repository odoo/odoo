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
        _computeOfflineMembers: () => ChannelMember[];
        allow_invite_by_email: Readonly<boolean>;
        allowCalls: Readonly<boolean>;
        allowDescription: Readonly<boolean>;
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
        default_display_mode: "video_full_screen"|undefined;
        executeCommand: (command: unknown, body: string) => unknown;
        fetchChannelInfoDeferred: Deferred<Thread|undefined>;
        fetchChannelInfoState: "not_fetched"|"fetching"|"fetched";
        fetchMoreAttachments: (limit: number) => Promise<void>;
        firstUnreadMessage: Message;
        group_ids: ResGroups[];
        hasMemberList: Readonly<boolean>;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<boolean>;
        invitationLink: Readonly<unknown|string>;
        invited_member_ids: ChannelMember[];
        last_interest_dt: import("luxon").DateTime;
        lastInterestDt: import("luxon").DateTime;
        lastMessageSeenByAllId: undefined|number;
        lastSelfMessageSeenByEveryone: Message;
        leaveChannel: () => Promise<void>;
        leaveChannelRpc: () => void;
        markAsFetched: () => Promise<void>;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        name: string;
        notifyAvatarToServer: (data: string) => Promise<void>;
        notifyDescriptionToServer: (description: unknown) => Promise<unknown>;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        rename: (name: string) => Promise<void>;
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        showCorrespondentCountry: Readonly<boolean>;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typesAllowingCalls: Readonly<string[]>;
    }

    export interface Models {
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
    }
}
