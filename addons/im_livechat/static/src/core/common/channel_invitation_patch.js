import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ChannelInvitation.prototype, {
    async fetchPartnersToInvite() {
        if (
            this.props.channel?.channel_type === "livechat" &&
            (this.props.channel?.livechat_end_dt || !this.store.has_access_livechat)
        ) {
            return;
        }
        return await super.fetchPartnersToInvite();
    },
    get showPartnersToInvite() {
        if (this.props.channel?.channel_type === "livechat") {
            return (
                !this.props.channel.livechat_end_dt &&
                this.store.has_access_livechat &&
                super.showPartnersToInvite
            );
        }
        return super.showPartnersToInvite;
    },
    get invitationTitle() {
        if (
            this.props.channel?.channel_type === "livechat" &&
            (this.props.channel.livechat_end_dt || !this.store.has_access_livechat)
        ) {
            return _t("Share Conversation");
        }
        return super.invitationTitle;
    },
});
