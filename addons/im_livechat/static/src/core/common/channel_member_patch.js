import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    get showAdminIcon() {
        return !this.props.member().isLivechatMember && super.showAdminIcon;
    },
    get showOwnerIcon() {
        return !this.props.member().isLivechatMember && super.showOwnerIcon;
    },
});
