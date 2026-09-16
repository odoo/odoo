import { MEMBER_CATEGORIES } from "@mail/discuss/core/common/channel_member_list";

import { _t } from "@web/core/l10n/translation";

MEMBER_CATEGORIES.push({
    sequence: 9,
    label: _t("Invited"),
    sequenceGroup: 10,
    icon: "schedule",
    headerClass: "text-warning pt-3",
    /** @param {import("models").DiscussChannel} channel */
    getMembers: (channel) =>
        [...channel.meeting_invited_member_ids].sort((m1, m2) => channel.store.sortMembers(m1, m2)),
});
