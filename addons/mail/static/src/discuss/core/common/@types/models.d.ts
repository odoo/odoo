declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";

    export interface ChannelMember extends ChannelMemberClass {}
    export interface DiscussChannel extends DiscussChannelClass {}

    export interface DiscussChannel {
        allowCalls: Readonly<boolean>;
        allowDescription: Readonly<boolean>;
        allowedToLeaveChannelTypes: Readonly<string[]>;
        allowedToUnpinChannelTypes: Readonly<string[]>;
        areAllMembersLoaded: Readonly<boolean>;
        avatar_cache_key: string;
        canLeave: Readonly<boolean>;
        canUnpin: Readonly<boolean>;
        channel: DiscussChannel;
        channel_member_ids: ChannelMember[];
        channel_name_member_ids: ChannelMember[];
        channel_type: string;
        correspondent: ChannelMember;
        correspondentCountry: Country;
        correspondents: Readonly<ChannelMember[]>;
        default_display_mode: "video_full_screen"|undefined;
        fetchChannelInfoDeferred: Deferred<Thread|undefined>;
        fetchChannelInfoState: "not_fetched"|"fetching"|"fetched";
        firstUnreadMessage: Message;
        group_ids: ResGroups[];
        hasMemberList: Readonly<boolean>;
        hasOtherMembersTyping: boolean;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<boolean>;
        invitationLink: Readonly<unknown|string>;
        invited_member_ids: ChannelMember[];
        isChatChannel: Readonly<boolean>;
        last_interest_dt: import("luxon").DateTime;
        lastInterestDt: import("luxon").DateTime;
        lastMessageSeenByAllId: undefined|number;
        lastSelfMessageSeenByEveryone: Message;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        member_count: number|undefined;
        membersThatCanSeen: Readonly<ChannelMember[]>;
        name: string;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        otherTypingMembers: ChannelMember[];
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        showCorrespondentCountry: Readonly<boolean>;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typesAllowingCalls: Readonly<string[]>;
        typingMembers: ChannelMember[];
        unknownMembersCount: Readonly<number>;
    }
    export interface MailGuest {
        channelMembers: ChannelMember[];
    }
    export interface Message {
        channelMemberHaveSeen: Readonly<ChannelMember[]>;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneFetched: boolean|undefined;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        threadAsFirstUnread: Thread;
    }
    export interface ResPartner {
        channelMembers: ChannelMember[];
    }
    export interface Store {
        channel_types_with_seen_infos: string[];
        channelIdsFetchingDeferred: Map<number, Deferred>;
        createGroupChat: (param0: { default_display_mode: string, partners_to: number[], name: string }) => Promise<Thread>;
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
        allowCalls: Readonly<boolean>;
        allowDescription: Readonly<boolean>;
        allowedToLeaveChannelTypes: Readonly<string[]>;
        allowedToUnpinChannelTypes: Readonly<string[]>;
        areAllMembersLoaded: Readonly<boolean>;
        avatar_cache_key: string;
        canLeave: Readonly<boolean>;
        canUnpin: Readonly<boolean>;
        channel: DiscussChannel;
        channel_member_ids: ChannelMember[];
        channel_name_member_ids: ChannelMember[];
        channel_type: string;
        computeCorrespondent: () => ChannelMember;
        correspondent: ChannelMember;
        correspondentCountry: Country;
        correspondents: Readonly<ChannelMember[]>;
        default_display_mode: "video_full_screen"|undefined;
        executeCommand: (command: unknown, body: string) => unknown;
        fetchChannelInfoDeferred: Deferred<Thread|undefined>;
        fetchChannelInfoState: "not_fetched"|"fetching"|"fetched";
        fetchChannelMembers: () => Promise<void>;
        fetchMoreAttachments: (limit: number) => Promise<void>;
        firstUnreadMessage: Message;
        group_ids: ResGroups[];
        hasMemberList: Readonly<boolean>;
        hasOtherMembersTyping: boolean;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<boolean>;
        invitationLink: Readonly<unknown|string>;
        invited_member_ids: ChannelMember[];
        isChatChannel: Readonly<boolean>;
        last_interest_dt: import("luxon").DateTime;
        lastInterestDt: import("luxon").DateTime;
        lastMessageSeenByAllId: undefined|number;
        lastSelfMessageSeenByEveryone: Message;
        leaveChannel: (param0: { force: boolean }) => Promise<void>;
        markAsFetched: () => Promise<void>;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        member_count: number|undefined;
        membersThatCanSeen: Readonly<ChannelMember[]>;
        name: string;
        notifyAvatarToServer: (data: string) => Promise<void>;
        notifyDescriptionToServer: (description: unknown) => Promise<unknown>;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        openChannel: () => boolean;
        otherTypingMembers: ChannelMember[];
        rename: (name: string) => Promise<void>;
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        showCorrespondentCountry: Readonly<boolean>;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typesAllowingCalls: Readonly<string[]>;
        typingMembers: ChannelMember[];
        unknownMembersCount: Readonly<number>;
    }

    export interface Models {
        "discuss.channel": DiscussChannel;
        "discuss.channel.member": ChannelMember;
    }
}
