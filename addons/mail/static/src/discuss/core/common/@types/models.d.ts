declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface Message {
        channelMemberHaveSeen: Readonly<unknown[]>;
        hasEveryoneSeen: boolean|undefined;
        hasNewMessageSeparator: boolean;
        hasSomeoneFetched: boolean|undefined;
        hasSomeoneSeen: boolean|undefined;
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean;
        mentionedChannelPromises: unknown[];
        threadAsFirstUnread: Thread;
    }
    export interface Persona {
        channelMembers: ChannelMember[];
    }
    export interface Store {
        "discuss.channel.member": ChannelMember;
        channel_types_with_seen_infos: unknown[];
        createGroupChat: ({ default_display_mode: unknown, partners_to: unknown, name: unknown }) => Promise<unknown>;
        fetchChannel: (channelId: unknown) => Promise<void>;
        getRecentChatPartnerIds: () => number[];
        onlineMemberStatuses: Readonly<string[]>;
        sortMembers: (m1: unknown, m2: unknown) => boolean;
        startChat: (partnerIds: [number]) => Promise<void>;
        updateBusSubscription: unknown;
    }
    export interface Thread {
        _computeOfflineMembers: () => unknown[];
        areAllMembersLoaded: Readonly<boolean>;
        channel_member_ids: ChannelMember[];
        computeCorrespondent: () => unknown;
        correspondent: ChannelMember;
        correspondents: Readonly<unknown[]>;
        default_display_mode: unknown;
        fetchChannelInfoDeferred: unknown;
        fetchChannelInfoState: string;
        fetchChannelMembers: () => Promise<undefined>;
        fetchMoreAttachments: (limit: number) => Promise<undefined>;
        firstUnreadMessage: Message;
        hasMemberList: Readonly<boolean>;
        hasOtherMembersTyping: boolean;
        hasSeenFeature: boolean;
        hasSelfAsMember: Readonly<unknown>;
        invitedMembers: ChannelMember[];
        last_interest_dt: luxon.DateTime;
        lastInterestDt: luxon.DateTime;
        lastMessageSeenByAllId: undefined|unknown[];
        lastSelfMessageSeenByEveryone: Message;
        member_count: unknown;
        membersThatCanSeen: Readonly<unknown>;
        name: unknown;
        offlineMembers: ChannelMember[];
        onlineMembers: ChannelMember[];
        otherTypingMembers: ChannelMember[];
        scrollUnread: boolean;
        selfMember: ChannelMember;
        showUnreadBanner: Readonly<boolean>;
        toggleBusSubscription: boolean;
        typingMembers: ChannelMember[];
        unknownMembersCount: Readonly<boolean>;
    }

    export interface Models {
        "discuss.channel.member": ChannelMember;
    }
}
