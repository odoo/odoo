import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { patch } from "@web/core/utils/patch";

patch(ChannelInvitation.prototype, {
    async fetchPartnersToInvite() {
        if (this.props.channel?.livechat_end_dt) {
            return;
        }
        return await super.fetchPartnersToInvite();
    },
    get showPartnersToInvite() {
        return super.showPartnersToInvite && !this.props.channel?.livechat_end_dt;
    },
});
