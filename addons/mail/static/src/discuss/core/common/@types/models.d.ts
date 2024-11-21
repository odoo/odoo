declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface Persona {
        channelMembers: ChannelMember[],
    }

    export interface Store {
        "discuss.channel.member": typeof ChannelMemberClass,
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
        hasOtherMembersTyping: boolean,
        readonly hasMemberList: boolean,
        readonly hasSelfAsMember: boolean,
        invitedMembers: ChannelMember[],
        member_count: number | undefined,
        readonly membersThatCanSeen: ChannelMember[],
        onlineMembers: ChannelMember[],
        offlineMembers: ChannelMember[],
        otherTypingMembers: ChannelMember[],
        selfMember: ChannelMember,
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
