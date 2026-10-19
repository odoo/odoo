import { MEMBER_CATEGORIES } from "@mail/discuss/core/common/channel_member_list";
import { _t } from "@web/core/l10n/translation";

MEMBER_CATEGORIES.push({
    sequence: 9,
    label: _t("Visitor"),
    /** @param {import("models").DiscussChannel} channel */
    getMembers: (channel) =>
        channel.channel_member_ids.filter((m) => m.livechat_member_type === "visitor"),
});
