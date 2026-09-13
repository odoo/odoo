declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface MailGuest {
        channelMembers: ChannelMember[];
    }
    export interface Message {
        channelMemberHaveSeen: Readonly<ChannelMember[]>;
        hasEveryoneSeen: boolean | undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneFetched: boolean | undefined;
        hasSomeoneSeen: boolean | undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        mentionedChannelPromises: Promise<Thread>[];
        threadAsFirstUnread: Thread;
    }
    export interface ResPartner {
        channelMembers: ChannelMember[];
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        channelIdsFetchingDeferred: Map<number, Deferred>;
        createGroupChat: (param0: {
            default_display_mode?: string;
            partners_to: number[];
            name?: string;
        }) => Promise<Thread>;
        "discuss.channel.member": StaticMailRecord<
            ChannelMember,
            typeof ChannelMemberClass
        >;
        fetchChannel: (channelId: number) => Promise<void>;
        getRecentChatPartnerIds: () => number[];
        onlineMemberStatuses: Readonly<string[]>;
        sortMembers: (m1: ChannelMember, m2: ChannelMember) => number;
        startChat: (partnerIds: number[]) => Promise<void>;
        updateBusSubscription: (() => unknown) & { cancel: () => void };
    }
    export interface Thread {
        notifyAvatarToServer(data: string): Promise<void>;
        notifyDescriptionToServer(description: string): Promise<void>;
        _setupMembershipFields(): void;
        _setupSeenStateFields(): void;
        _setupChannelStateFields(): void;
        _computeFirstUnreadMessage(): Message | null;
        _computeLastMessageSeenByAllId(): number | string | undefined;
        _maxMessageIdByOthers(
            fieldName: "seen_message_id" | "fetched_message_id",
        ): number;
        _computeMaxSeenMessageIdByOthers(): number;
        _computeMaxFetchedMessageIdByOthers(): number;
        _computeLastSelfMessageSeenByEveryone(): Message | false | undefined;
        _computeOfflineMembers(): ChannelMember[];
        allow_invite_by_email: Readonly<boolean>;
        allowedToLeaveChannelTypes: Readonly<string[]>;
        allowedToUnpinChannelTypes: Readonly<string[]>;
        areAllMembersLoaded: Readonly<boolean>;
        avatar_cache_key: string;
        channel_member_ids: ChannelMember[];
        channel_name_member_ids: ChannelMember[];
        channel_type: string;
        computeCorrespondent: () => ChannelMember;
        correspondent: ChannelMember;
        correspondentCountry: Country;
        correspondents: Readonly<ChannelMember[]>;
        default_display_mode: "video_full_screen" | undefined;
        executeCommand: (
            command: import("@mail/discuss/core/common/channel_commands").ChannelCommand,
            body?: string,
        ) => Promise<any>;
        fetchChannelInfoState: "not_fetched" | "fetching" | "fetched";
        fetchChannelMembers: () => Promise<void>;
        fetchMoreAttachments: (limit?: number) => Promise<void>;
        firstUnreadMessage: Message;
        group_ids: ResGroups[];
        has_mail_thread: boolean | undefined;
        hasMemberList: Readonly<boolean>;
        isMultiMemberChannel: Readonly<boolean>;
        isMuted: Readonly<boolean>;
        hasOtherMembersTyping: boolean;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<boolean>;
        invited_member_ids: ChannelMember[];
        last_interest_dt: import("luxon").DateTime;
        lastInterestDt: import("luxon").DateTime;
        lastMessageSeenByAllId: undefined | number;
        lastSelfMessageSeenByEveryone: Message;
        leaveChannel: (options?: { force?: boolean }) => Promise<boolean>;
        markAsFetched: () => Promise<void>;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        markReadSequential: ReturnType<
            typeof import("@mail/utils/common/misc").makeSequential
        >;
        maxFetchedMessageIdByOthers: number;
        maxSeenMessageIdByOthers: number;
        member_count: number | undefined;
        membersThatCanSeen: Readonly<ChannelMember[]>;
        name: string;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        openChannel: () => boolean;
        otherTypingMembers: ChannelMember[];
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        shouldSubscribeToBusChannel: Readonly<boolean>;
        showCorrespondentCountry: Readonly<boolean>;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typesAllowingCalls: Readonly<string[]>;
        typingMembers: ChannelMember[];
        unknownMembersCount: Readonly<number>;
    }

    export interface Models {
        "discuss.channel.member": ChannelMember;
    }
}
