import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { fields, patchModel } from "@mail/model/export";

ChannelMember.CANCEL_CALL_INVITE_DELAY = 30000;
export const ChannelMemberPatch = patchModel(ChannelMember, {
    setup() {
        super.setup(...arguments);
        this.rtc_inviting_session_id = fields.One("discuss.channel.rtc.session");
        this.onEnter(
            () => [this.rtc_inviting_session_id],
            (session) => {
                if (!this.channel_id) {
                    return;
                }
                this.channel_id.rtc_session_ids.add(session);
                this.store.ringingChannels.add(this.channel_id);
                this.startInvitationTimeout();
                return () => {
                    if (!this.channel_id) {
                        return;
                    }
                    this.cancelInvitationTimeout();
                    this.store.ringingChannels.delete(this.channel_id);
                };
            }
        );
        this.rtcSession = fields.One("discuss.channel.rtc.session");
    },
    cancelInvitationTimeout() {
        if (this.channel_id?.cancelRtcInvitationTimeout) {
            window.clearTimeout(this.channel_id.cancelRtcInvitationTimeout);
            this.channel_id.cancelRtcInvitationTimeout = undefined;
        }
    },
    startInvitationTimeout() {
        if (this.channel_id.cancelRtcInvitationTimeout) {
            return;
        }
        this.channel_id.cancelRtcInvitationTimeout = window.setTimeout(() => {
            this.store.rtc.leaveCall(this.channel_id);
            this.channel_id.cancelRtcInvitationTimeout = undefined;
        }, ChannelMember.CANCEL_CALL_INVITE_DELAY);
    },
});
