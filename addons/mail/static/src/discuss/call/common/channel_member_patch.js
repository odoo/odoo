import { ChannelMember } from "@mail/discuss/core/common/channel_member";

import { patch } from "@web/core/utils/patch";

/** @type {ChannelMember} */
const ChannelMemberPatch = {
    /**
     * The member's live call session, or undefined when the member has only been invited (ringing)
     * and has not joined yet. `rtc_inviting_session_id` is only sent for the current user, so a
     * pending invitee is detected through the channel's invited list instead.
     */
    get callSession() {
        const member = this.member();
        if (member.in(member.channel_id?.invited_member_ids)) {
            return undefined;
        }
        return member.rtcSession;
    },
    /**
     * Highlight the avatar while the member is actively talking, mirroring the
     * sidebar call participants indicator.
     */
    get avatarClass() {
        return {
            ...super.avatarClass,
            "o-isTalking": Boolean(
                this.member().channel_id?.isSelfInCall && this.callSession?.isActuallyTalking
            ),
        };
    },
};
patch(ChannelMember.prototype, ChannelMemberPatch);
