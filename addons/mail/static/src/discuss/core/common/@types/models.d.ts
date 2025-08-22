declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface Message {
        channelMemberHaveSeen: Readonly<ChannelMember[]>;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneFetched: boolean|undefined;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        mentionedChannelPromises: Promise<Thread>[];
        threadAsFirstUnread: Thread;
    }
    export interface Persona {
        channelMembers: ChannelMember[];
    }
    export interface Store {
        channelIdsFetchingDeferred: Map<number, Deferred>;
        channel_types_with_seen_infos: string[];
        createGroupChat: (param0: { default_display_mode: string, partners_to: number[], name: string }) => Promise<Thread>;
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
        areAllMembersLoaded: Readonly<boolean>;
        channel_member_ids: ChannelMember[];
        computeCorrespondent: () => ChannelMember;
        correspondent: ChannelMember;
        correspondents: Readonly<ChannelMember[]>;
        default_display_mode: "video_full_screen"|undefined;
        fetchChannelInfoDeferred: Deferred<Thread|undefined>;
        fetchChannelInfoState: "not_fetched"|"fetching"|"fetched";
        fetchChannelMembers: () => Promise<void>;
        fetchMoreAttachments: (limit: number) => Promise<void>;
        firstUnreadMessage: Message;
        hasMemberList: Readonly<boolean>;
        hasOtherMembersTyping: boolean;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<boolean>;
        invited_member_ids: ChannelMember[];
        last_interest_dt: luxon.DateTime;
        lastInterestDt: luxon.DateTime;
        lastMessageSeenByAllId: undefined|number;
        lastSelfMessageSeenByEveryone: Message;
        markedAsUnread: boolean;
        markingAsRead: boolean;
        markReadSequential: () => Promise<any>;
        member_count: number|undefined;
        membersThatCanSeen: Readonly<ChannelMember[]>;
        name: string;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        otherTypingMembers: ChannelMember[];
        scrollUnread: boolean;
        self_member_id: ChannelMember;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typingMembers: ChannelMember[];
        unknownMembersCount: Readonly<number>;
    }

    export interface Models {
        "discuss.channel.member": ChannelMember;
    }
}
