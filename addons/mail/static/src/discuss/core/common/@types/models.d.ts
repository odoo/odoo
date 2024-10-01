declare module "models" {
    import { ChannelMember as ChannelMemberClass } from "@mail/discuss/core/common/channel_member_model";

    export interface ChannelMember extends ChannelMemberClass {}

    export interface Persona {
        channelMembers: ChannelMember[],
    }

    export interface Store {
        "discuss.channel.member": typeof ChannelMemberClass,
        readonly onlineMemberStatuses: String[],
        sortMembers(m1: ChannelMember, m2: ChannelMember)
    }

    export interface Thread {
        channelMembers: ChannelMember[],
        channel_type: "chat" | "channel" | "group" | "livechat" | "whatsapp",
        computeCorrespondent(): ChannelMember | undefined,
        correspondent: ChannelMember,
        hasOtherMembersTyping: boolean,
        readonly hasMemberList: boolean,
        readonly hasSelfAsMember: boolean,
        invitedMembers: ChannelMember[],
        readonly membersThatCanSeen: ChannelMember[],
        onlineMembers: ChannelMember[],
        offlineMembers: ChannelMember[],
        otherTypingMembers: ChannelMember[],
        selfMember: ChannelMember,
        typingMembers: ChannelMember[],
        readonly hasMemberList: boolean,
        readonly notifyOnleave: boolean,
        private _computeOfflineMembers(): ChannelMember[],
    }

    export interface Models {
        "discuss.channel.member": ChannelMember,
    }
}
