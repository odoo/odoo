import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { fields } from "@mail/model/export";

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

ChannelMember.CANCEL_CALL_INVITE_DELAY = 30000;
/** @type {import("models").ChannelMember} */
const ChannelMemberPatch = {
    setup() {
        super.setup(...arguments);
        this.rtc_inviting_session_id = fields.One("discuss.channel.rtc.session", {
            /** @this {import("models").ChannelMember} */
            onAdd(r) {
                if (!this.channel_id) {
                    return;
                }
                this.channel_id.rtc_session_ids.add(r);
                this.store.ringingChannels.add(this.channel_id);
                this.startInvitationTimeout();
            },
            /** @this {import("models").ChannelMember} */
            onDelete() {
                if (!this.channel_id) {
                    return;
                }
                this.cancelInvitationTimeout();
                this.store.ringingChannels.delete(this.channel_id);
            },
        });
        this.rtcSession = fields.One("discuss.channel.rtc.session");
    },
    cancelInvitationTimeout() {
        if (this.channel_id?.cancelRtcInvitationTimeout) {
            browser.clearTimeout(this.channel_id.cancelRtcInvitationTimeout);
            this.channel_id.cancelRtcInvitationTimeout = undefined;
        }
    },
    startInvitationTimeout() {
        if (this.channel_id.cancelRtcInvitationTimeout) {
            return;
        }
        this.channel_id.cancelRtcInvitationTimeout = browser.setTimeout(() => {
            this.store.rtc.leaveCall(this.channel_id);
            this.channel_id.cancelRtcInvitationTimeout = undefined;
        }, ChannelMember.CANCEL_CALL_INVITE_DELAY);
    },
};
patch(ChannelMember.prototype, ChannelMemberPatch);
