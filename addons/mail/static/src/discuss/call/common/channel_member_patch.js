import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { fields } from "@mail/core/common/record";

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
                this.store.ringingThreads.add(this.channel_id);
                this.channel_id.cancelRtcInvitationTimeout = browser.setTimeout(() => {
                    this.store.env.services["discuss.rtc"].leaveCall(this.channel_id);
                }, ChannelMember.CANCEL_CALL_INVITE_DELAY);
            },
            /** @this {import("models").ChannelMember} */
            onDelete() {
                if (!this.channel_id) {
                    return;
                }
                browser.clearTimeout(this.channel_id.cancelRtcInvitationTimeout);
                this.store.ringingThreads.delete(this.channel_id);
            },
        });
        this.rtcSession = fields.One("discuss.channel.rtc.session");
    },
};
patch(ChannelMember.prototype, ChannelMemberPatch);
