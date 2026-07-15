import { MEMBER_CATEGORIES } from "@mail/discuss/core/common/channel_member_list";

import { _t } from "@web/core/l10n/translation";

MEMBER_CATEGORIES.push(
    {
        sequence: 5,
        label: _t("In this call"),
        sequenceGroup: 10,
        icon: "fa fa-video-camera",
        headerClass: "text-success pt-0",
        /** @param {import("models").DiscussChannel} channel */
        getMembers: (channel) =>
            channel.rtc_session_ids
                .map((session) => session.channel_member_id)
                .filter((member) => member && !member.in(channel.invited_member_ids))
                .sort((m1, m2) => channel.store.sortMembers(m1, m2)),
    },
    {
        sequence: 8,
        label: _t("Also invited"),
        sequenceGroup: 10,
        icon: "fa fa-clock-o",
        headerClass: "text-warning pt-3",
        /** @param {import("models").DiscussChannel} channel */
        getMembers: (channel) =>
            [...channel.invited_member_ids].sort((m1, m2) => channel.store.sortMembers(m1, m2)),
    }
);
