declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface Message {
        readonly channelMemberHaveSeen: ChannelMember[],
        hasEveryoneSeen: boolean,
        hasNewMessageSeparator: boolean,
        hasSomeoneFetched: boolean,
        hasSomeoneSeen: boolean,
        isMessagePreviousToLastSelfMessageSeenByEveryone: boolean,
        mentionedChannelPromises: Promise<Thread>[],
        threadAsFirstUnread: Thread,
    }

    export interface Persona {
        channelMembers: ChannelMember[],
    }

    export interface Store {
        channel_types_with_seen_infos: string[],
        "discuss.channel.member": typeof ChannelMemberClass,
        fetchChannel(channelId: number): Promise<void>,
        getRecentChatPartnerIds(): number[],
        readonly onlineMemberStatuses: String[],
        sortMembers(m1: ChannelMember, m2: ChannelMember)
    }

    export interface Thread {
        readonly areAllMembersLoaded: boolean,
        channel_member_ids: ChannelMember[],
        channel_type: "chat" | "channel" | "group" | "livechat" | "whatsapp",
        computeCorrespondent(): ChannelMember | undefined,
        correspondent: ChannelMember,
        readonly correspondents: ChannelMember[],
        default_display_mode: "video_full_screen" | false | undefined,
        fetchChannelMembers(): Promise<void>,
        firstUnreadMessage: Message,
        hasOtherMembersTyping: boolean,
        readonly hasMemberList: boolean,
        readonly hasSeenFeature: boolean,
        readonly hasSelfAsMember: boolean,
        invitedMembers: ChannelMember[],
        last_interest_dt: luxon.DateTime,
        lastInterestDt: luxon.DateTime,
        readonly lastMessageSeenByAllId: number,
        readonly lastSelfMessageSeenByEveryone: Message,
        member_count: number | undefined,
        readonly membersThatCanSeen: ChannelMember[],
        name: string,
        newMessageBannerText: string,
        onClickUnreadMessagesBanner(): void,
        onlineMembers: ChannelMember[],
        offlineMembers: ChannelMember[],
        otherTypingMembers: ChannelMember[],
        selfMember: ChannelMember,
        showUnreadBanner(): boolean,
        typingMembers: ChannelMember[],
        readonly hasMemberList: boolean,
        readonly notifyOnleave: boolean,
        readonly unknownMembersCount: number,
        private _computeOfflineMembers(): ChannelMember[],
    }

    export interface Models {
        "discuss.channel.member": ChannelMember,
    }
}
