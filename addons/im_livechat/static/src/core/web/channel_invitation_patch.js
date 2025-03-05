import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ChannelInvitation.prototype, {
    get searchPlaceholder() {
        if (this.props.thread?.channel_type === "livechat") {
            return _t("Search people, languages or expertise");
        }
        return super.searchPlaceholder;
    },
});
